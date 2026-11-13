const workerUrl = import.meta.env.VITE_WEBRTC_WORKER_URL

export type ClientSession = {
  peer: RTCPeerConnection
  channel: RTCDataChannel
  sdp: string
}

let clientSession: Promise<ClientSession> | undefined

export function getClientSession() {
  clientSession ??= createClientSession()
  return clientSession
}

export function createIndependentClientSession() {
  return createClientSession()
}

export async function resetClientSession() {
  const activeSession = clientSession
  clientSession = undefined
  if (activeSession) {
    const { peer } = await activeSession
    peer.close()
  }
}

export async function sendAndReceive(session: ClientSession, message: unknown, matches: (response: Record<string, unknown>) => boolean) {
  const response = receiveMessage(session.channel, matches)
  session.channel.send(JSON.stringify(message))
  return response
}

export function receiveMessage(channel: RTCDataChannel, matches: (response: Record<string, unknown>) => boolean) {
  return new Promise<Record<string, unknown>>((resolveMessage, rejectMessage) => {
    const timeout = window.setTimeout(() => {
      channel.removeEventListener('message', receive)
      rejectMessage(new Error('Timed out waiting for a data-channel response'))
    }, 10000)

    function receive(event: MessageEvent<string>) {
      const response = JSON.parse(event.data) as Record<string, unknown>
      if (!matches(response)) {
        return
      }
      window.clearTimeout(timeout)
      channel.removeEventListener('message', receive)
      resolveMessage(response)
    }

    channel.addEventListener('message', receive)
  })
}

async function createClientSession(): Promise<ClientSession> {
  const iceResponse = await fetch(`${workerUrl}/ice-configuration`)
  if (!iceResponse.ok) {
    throw new Error(`TURN configuration returned HTTP ${iceResponse.status}`)
  }
  const configuration = await iceResponse.json() as RTCConfiguration
  const peer = new RTCPeerConnection({ ...configuration, iceTransportPolicy: 'relay' })
  const channel = peer.createDataChannel('data')

  try {
    await peer.setLocalDescription(await peer.createOffer())
    await waitForIceGathering(peer)
    const response = await fetch(`${workerUrl}/offer`, {
      method: 'POST',
      headers: { 'content-type': 'application/sdp' },
      body: peer.localDescription?.sdp,
    })
    if (!response.ok) {
      throw new Error(`SDP negotiation returned HTTP ${response.status}`)
    }

    const sdp = await response.text()
    await peer.setRemoteDescription({ type: 'answer', sdp })
    await waitForDataChannel(channel)
    return { peer, channel, sdp }
  } catch (error) {
    peer.close()
    throw error
  }
}

function waitForIceGathering(peer: RTCPeerConnection) {
  if (peer.iceGatheringState === 'complete') {
    return Promise.resolve()
  }
  return new Promise<void>((resolveGathering, rejectGathering) => {
    const timeout = window.setTimeout(() => {
      peer.removeEventListener('icegatheringstatechange', checkGathering)
      rejectGathering(new Error('Timed out gathering ICE candidates'))
    }, 20000)

    function checkGathering() {
      if (peer.iceGatheringState !== 'complete') {
        return
      }
      window.clearTimeout(timeout)
      peer.removeEventListener('icegatheringstatechange', checkGathering)
      resolveGathering()
    }

    peer.addEventListener('icegatheringstatechange', checkGathering)
  })
}

function waitForDataChannel(channel: RTCDataChannel) {
  if (channel.readyState === 'open') {
    return Promise.resolve()
  }
  return new Promise<void>((resolveOpen, rejectOpen) => {
    const timeout = window.setTimeout(() => {
      channel.removeEventListener('open', open)
      rejectOpen(new Error('Timed out opening the data channel'))
    }, 20000)

    function open() {
      window.clearTimeout(timeout)
      channel.removeEventListener('open', open)
      resolveOpen()
    }

    channel.addEventListener('open', open)
  })
}
