import { createServer, type IncomingMessage, type ServerResponse } from 'node:http'
import { api } from '../dist/webrtc.schema.js'
import { RTCPeerConnection, type RTCDataChannel } from 'werift'

type Session = {
  peer: RTCPeerConnection
  sdp: string
}

type Stream = {
  interrupted: boolean
}

const port = Number(process.env.PORT)
const sessions = new Set<Session>()

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('PORT must be an integer between 1 and 65535')
}

const server = createServer(handleRequest)

server.on('close', () => {
  sessions.forEach(({ peer }) => void peer.close())
  sessions.clear()
})

server.listen(port, '127.0.0.1')

async function handleRequest(request: IncomingMessage, response: ServerResponse) {
  setCorsHeaders(response)

  if (request.method === 'OPTIONS') {
    response.writeHead(204).end()
    return
  }

  if (request.method === 'GET' && ['/','/health'].includes(request.url ?? '')) {
    response.writeHead(200, { 'content-type': 'text/plain' }).end('ok')
    return
  }

  if (request.method === 'GET' && request.url === '/ice-configuration') {
    await sendIceConfiguration(response)
    return
  }

  if (request.method === 'POST' && request.url === '/offer') {
    await negotiateOffer(request, response)
    return
  }

  response.writeHead(404).end()
}

function setCorsHeaders(response: ServerResponse) {
  response.setHeader('access-control-allow-origin', '*')
  response.setHeader('access-control-allow-methods', 'GET, POST, OPTIONS')
  response.setHeader('access-control-allow-headers', 'Content-Type')
}

async function sendIceConfiguration(response: ServerResponse) {
  try {
    const configuration = await getIceConfiguration()
    response.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify(configuration))
  } catch {
    response.writeHead(503).end()
  }
}

async function negotiateOffer(request: IncomingMessage, response: ServerResponse) {
  try {
    const sdp = await readBody(request)
    if (!sdp) {
      response.writeHead(400).end()
      return
    }

    const session = await answerOffer(sdp)
    sessions.add(session)
    session.peer.connectionStateChange.subscribe((state) => {
      if (state === 'failed' || state === 'closed') {
        closeSession(session)
      }
    })
    response.writeHead(200, { 'content-type': 'application/sdp' }).end(session.sdp)
  } catch {
    response.writeHead(400).end()
  }
}

async function readBody(request: IncomingMessage) {
  const chunks = await request.toArray()
  return Buffer.concat(chunks.map((chunk) => Buffer.from(chunk))).toString()
}

async function getIceConfiguration() {
  const token = process.env.SECRET_HUGGINGFACE_TOKEN
  if (!token) {
    throw new Error('SECRET_HUGGINGFACE_TOKEN is required')
  }

  const response = await fetch('https://fastrtc-turn-service.hf.space/credentials?ttl=600', {
    headers: { authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    throw new Error(`TURN credentials returned ${response.status}`)
  }

  return api.shape.ice_configuration.parse(await response.json())
}

async function answerOffer(sdp: string): Promise<Session> {
  const configuration = await getIceConfiguration()
  const peer = new RTCPeerConnection({ ...configuration, iceTransportPolicy: 'all', iceUseDefaultStunServer: false })
  peer.ondatachannel = ({ channel }) => receiveMessages(channel)

  try {
    await peer.setRemoteDescription({ type: 'offer', sdp })
    await peer.setLocalDescription(await peer.createAnswer())
    if (peer.iceGatheringState !== 'complete') {
      await peer.iceGatheringStateChange.watch((state) => state === 'complete', 10000)
    }
    const answer = peer.localDescription?.sdp
    if (!answer) {
      throw new Error('SDP answer unavailable')
    }
    return { peer, sdp: answer }
  } catch (error) {
    await peer.close()
    throw error
  }
}

function receiveMessages(channel: RTCDataChannel) {
  const streams = new Map<string, Stream>()
  channel.onMessage.subscribe((message) => handleMessage(channel, streams, message.toString()))
}

function handleMessage(channel: RTCDataChannel, streams: Map<string, Stream>, message: string) {
  let value: unknown
  try {
    value = JSON.parse(message)
  } catch {
    sendOutputMessage(channel, { type: 'error', error: 'Invalid input' })
    return
  }

  const parsed = api.shape.input.safeParse(value)
  if (!parsed.success) {
    sendOutputMessage(channel, { type: 'error', error: 'Invalid input' })
    return
  }

  const input = parsed.data
  if (input.type === 'input') {
    sendOutput(channel, input.id, input.value)
    return
  }
  if (input.type === 'interrupt') {
    interruptStream(channel, streams, input.id)
    return
  }
  startStream(channel, streams, input.id, input.values)
}

function sendOutput(channel: RTCDataChannel, id: string, value: unknown) {
  sendOutputMessage(channel, { type: 'output', id, value })
}

function sendOutputMessage(channel: RTCDataChannel, value: unknown) {
  channel.send(JSON.stringify(api.shape.output.parse(value)))
}

function startStream(channel: RTCDataChannel, streams: Map<string, Stream>, id: string, values: unknown[]) {
  if (streams.has(id)) {
    sendOutputMessage(channel, { type: 'error', error: 'Operation already running' })
    return
  }

  const stream = { interrupted: false }
  streams.set(id, stream)
  sendStreamChunk(channel, streams, id, stream, values, 0)
}

function sendStreamChunk(channel: RTCDataChannel, streams: Map<string, Stream>, id: string, stream: Stream, values: unknown[], index: number) {
  if (stream.interrupted || index === values.length) {
    sendOutputMessage(channel, { type: stream.interrupted ? 'interrupted' : 'done', id })
    streams.delete(id)
    return
  }

  sendOutputMessage(channel, { type: 'chunk', id, index, value: values[index] })
  setTimeout(() => sendStreamChunk(channel, streams, id, stream, values, index + 1), 50)
}

function interruptStream(channel: RTCDataChannel, streams: Map<string, Stream>, id: string) {
  const stream = streams.get(id)
  if (stream) {
    stream.interrupted = true
  } else {
    sendOutputMessage(channel, { type: 'error', error: 'Operation not running' })
  }
}

function closeSession(session: Session) {
  sessions.delete(session)
  void session.peer.close()
}
