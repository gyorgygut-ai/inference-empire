import { spawn, type ChildProcess } from 'node:child_process'
import { createServer as createTcpServer } from 'node:net'
import { resolve } from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { RTCPeerConnection, type RTCDataChannel, type RTCIceCandidateStats, type RTCIceServer } from 'werift'

export async function withWorker<T>(run: (url: string) => Promise<T>): Promise<T> {
  const port = await getAvailablePort()
  const worker = spawn(process.execPath, [resolve('node_modules/tsx/dist/cli.mjs'), 'apps/workers/webrtc/src/server.ts'], {
    env: { ...process.env, PORT: String(port) },
    stdio: 'ignore',
  })
  const url = `http://127.0.0.1:${port}`

  try {
    await waitForWorker(worker, url)
    return await run(url)
  } finally {
    await stopWorker(worker)
  }
}

export async function connectClient(url: string, iceServers?: RTCIceServer[], relayOnly = false) {
  const peer = new RTCPeerConnection({ iceServers: iceServers ?? [], iceTransportPolicy: relayOnly ? 'relay' : 'all', iceUseDefaultStunServer: false, turnTransport: relayOnly ? 'udp' : undefined })
  const channel = peer.createDataChannel('data')
  await peer.setLocalDescription(await peer.createOffer())
  if (peer.iceGatheringState !== 'complete') {
    await peer.iceGatheringStateChange.watch((state) => state === 'complete', 15000)
  }

  const response = await fetch(`${url}/offer`, {
    method: 'POST',
    headers: { 'content-type': 'application/sdp' },
    body: peer.localDescription?.sdp,
  })
  if (!response.ok) {
    await peer.close()
    throw new Error(`Offer failed with HTTP ${response.status}`)
  }

  await peer.setRemoteDescription({ type: 'answer', sdp: await response.text() })
  try {
    await channel.stateChange.watch((state) => state === 'open', 15000)
  } catch (error) {
    const state = `ICE ${peer.iceConnectionState}, peer ${peer.connectionState}`
    const stats = [...(await peer.getStats()).values()]
    const candidates = stats.filter((stat): stat is RTCIceCandidateStats => stat.type === 'local-candidate').map((stat) => stat.candidateType)
    await peer.close()
    throw new Error(`Data channel did not open: ${state}; local candidates ${candidates.join(', ')}`, { cause: error })
  }
  return { peer, channel }
}

export async function receiveMessage(channel: RTCDataChannel) {
  const [message] = await channel.onMessage.asPromise(10000)
  return JSON.parse(message.toString()) as Record<string, unknown>
}

export async function exchange(channel: RTCDataChannel, input: unknown) {
  const response = receiveMessage(channel)
  channel.send(JSON.stringify(input))
  return response
}

export async function closeClients(...peers: RTCPeerConnection[]) {
  await Promise.all(peers.map((peer) => peer.close()))
}

async function getAvailablePort() {
  const server = createTcpServer()
  await new Promise<void>((resolveListen) => server.listen(0, '127.0.0.1', resolveListen))
  const address = server.address()
  if (!address || typeof address === 'string') {
    throw new Error('Unable to reserve a worker port')
  }
  await new Promise<void>((resolveClose, rejectClose) => server.close((error) => error ? rejectClose(error) : resolveClose()))
  return address.port
}

async function waitForWorker(worker: ChildProcess, url: string, attempts = 100): Promise<void> {
  if (worker.exitCode !== null) {
    throw new Error(`Worker exited with code ${worker.exitCode}`)
  }

  try {
    const response = await fetch(url)
    if (response.ok) {
      return
    }
  } catch {
    if (attempts === 0) {
      throw new Error(`Worker did not listen on ${url}`)
    }
  }

  if (attempts === 0) {
    throw new Error(`Worker did not listen on ${url}`)
  }
  await delay(50)
  return waitForWorker(worker, url, attempts - 1)
}

async function stopWorker(worker: ChildProcess) {
  if (worker.exitCode !== null) {
    return
  }
  const exited = new Promise<void>((resolveExit) => worker.once('exit', () => resolveExit()))
  worker.kill('SIGTERM')
  await exited
}
