"use client"

import {
  createRealtimeEventEmitter,
  type AudioVisualization,
  type RealtimeAdapter,
  type RealtimeToken,
} from "@tanstack/ai"

const emptyAudioData = () => new Uint8Array(0)

const audioVisualization: AudioVisualization = {
  inputLevel: 0,
  outputLevel: 0,
  inputSampleRate: 0,
  outputSampleRate: 0,
  getInputFrequencyData: emptyAudioData,
  getOutputFrequencyData: emptyAudioData,
  getInputTimeDomainData: emptyAudioData,
  getOutputTimeDomainData: emptyAudioData,
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value)

const isIceServer = (value: unknown): value is RTCIceServer => {
  if (!isRecord(value)) return false
  const urls = value.urls
  const validUrls = typeof urls === "string" ||
    (Array.isArray(urls) && urls.length > 0 && urls.every((url) => typeof url === "string"))
  return validUrls &&
    (value.username === undefined || typeof value.username === "string") &&
    (value.credential === undefined || typeof value.credential === "string") &&
    (value.credentialType === undefined ||
      value.credentialType === "password" ||
      value.credentialType === "oauth")
}

const readRtcConfiguration = (value: unknown): RTCConfiguration => {
  if (!isRecord(value) || !Array.isArray(value.iceServers)) {
    throw new Error("Voice session is missing TURN configuration")
  }
  const iceServers = value.iceServers.filter(isIceServer)
  const hasTurnRelay = iceServers.some((server) => {
    const urls = typeof server.urls === "string" ? [server.urls] : server.urls
    return urls.some((url) => /^turns?:/i.test(url))
  })
  if (!hasTurnRelay) throw new Error("Voice session does not include a TURN relay")

  const policy = value.iceTransportPolicy
  if (policy !== undefined && policy !== "all" && policy !== "relay") {
    throw new Error("Voice session has an invalid ICE transport policy")
  }
  return {
    iceServers,
    ...(policy === undefined ? {} : { iceTransportPolicy: policy }),
  }
}

const waitForPeerState = (
  peer: RTCPeerConnection,
  expectedState: RTCPeerConnectionState,
) =>
  new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => {
      peer.removeEventListener("connectionstatechange", onStateChange)
      reject(new Error(`WebRTC connection timed out before ${expectedState}`))
    }, 45_000)

    const onStateChange = () => {
      if (peer.connectionState === expectedState) {
        clearTimeout(timeout)
        peer.removeEventListener("connectionstatechange", onStateChange)
        resolve()
      } else if (peer.connectionState === "failed" || peer.connectionState === "closed") {
        clearTimeout(timeout)
        peer.removeEventListener("connectionstatechange", onStateChange)
        reject(new Error(`WebRTC connection entered ${peer.connectionState}`))
      }
    }

    if (peer.connectionState === expectedState) {
      clearTimeout(timeout)
      resolve()
    } else {
      peer.addEventListener("connectionstatechange", onStateChange)
      onStateChange()
    }
  })

const waitForIceGathering = (peer: RTCPeerConnection) =>
  new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => {
      peer.removeEventListener("icegatheringstatechange", onStateChange)
      peer.removeEventListener("connectionstatechange", onStateChange)
      reject(new Error("WebRTC ICE gathering timed out"))
    }, 30_000)

    const onStateChange = () => {
      if (peer.iceGatheringState === "complete") {
        clearTimeout(timeout)
        peer.removeEventListener("icegatheringstatechange", onStateChange)
        peer.removeEventListener("connectionstatechange", onStateChange)
        resolve()
      } else if (peer.connectionState === "failed") {
        clearTimeout(timeout)
        peer.removeEventListener("icegatheringstatechange", onStateChange)
        peer.removeEventListener("connectionstatechange", onStateChange)
        reject(new Error("WebRTC ICE negotiation failed"))
      }
    }

    if (peer.iceGatheringState === "complete") {
      clearTimeout(timeout)
      resolve()
      return
    }

    peer.addEventListener("icegatheringstatechange", onStateChange)
    peer.addEventListener("connectionstatechange", onStateChange)
  })

export const postFastRtcOffer = async (workerUrl: string, token: string, sdp: string) => {
  const form = new FormData()
  form.set("sdp", sdp)

  const response = await fetch(`${workerUrl.replace(/\/$/, "")}/v1/realtime/calls`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
    cache: "no-store",
    signal: AbortSignal.timeout(45_000),
  })

  if (!response.ok) throw new Error("Voice worker rejected the WebRTC offer")
  const answer = await response.text()
  if (!answer.trim()) throw new Error("Voice worker returned an empty WebRTC answer")
  return answer
}

const connectFastRtc = async (
  workerUrl: string,
  token: string,
  rtcConfiguration: RTCConfiguration,
) => {
  if (!workerUrl) throw new Error("Voice worker URL is not configured")

  const peer = new RTCPeerConnection(rtcConfiguration)
  const audioTransceiver = peer.addTransceiver("audio", { direction: "sendrecv" })
  const dataChannel = peer.createDataChannel("text")
  const audio = document.createElement("audio")
  audio.autoplay = true

  try {
    peer.addEventListener("track", ({ streams }) => {
      const [stream] = streams
      if (!stream) return
      audio.srcObject = stream
      void audio.play().catch(() => undefined)
    })

    const offer = await peer.createOffer()
    await peer.setLocalDescription(offer)
    await waitForIceGathering(peer)

    const localDescription = peer.localDescription
    if (!localDescription?.sdp || !localDescription.type) {
      throw new Error("Unable to create WebRTC offer")
    }

    const answer = await postFastRtcOffer(workerUrl, token, localDescription.sdp)
    await peer.setRemoteDescription({ sdp: answer, type: "answer" })
    await waitForPeerState(peer, "connected")

    return { peer, audioTransceiver, dataChannel, audio }
  } catch (error) {
    dataChannel.close()
    audio.pause()
    audio.srcObject = null
    peer.close()
    throw error
  }
}

export const fastRtcAdapter: RealtimeAdapter = {
  provider: "worker-voice",

  async connect(token: RealtimeToken) {
    const workerUrl: unknown = token.config.providerOptions?.workerUrl
    if (typeof workerUrl !== "string" || !workerUrl) {
      throw new Error("Voice worker URL is not configured")
    }
    const rtcConfiguration = readRtcConfiguration(
      token.config.providerOptions?.rtcConfiguration,
    )
    const { peer, audioTransceiver, dataChannel, audio } = await connectFastRtc(
      workerUrl,
      token.token,
      rtcConfiguration,
    )
    const events = createRealtimeEventEmitter()
    let localStream: MediaStream | undefined

    peer.addEventListener("connectionstatechange", () => {
      if (peer.connectionState === "connected") {
        events.emit("status_change", { status: "connected" })
      } else if (peer.connectionState === "failed") {
        events.emit("status_change", { status: "error" })
        events.emit("error", { error: new Error("Voice connection failed") })
      } else if (peer.connectionState === "disconnected") {
        events.emit("status_change", { status: "reconnecting" })
      }
    })

    dataChannel.addEventListener("message", ({ data }) => {
      if (typeof data !== "string") return

      let message: unknown
      try {
        message = JSON.parse(data)
      } catch {
        return
      }

      if (
        typeof message !== "object" ||
        message === null ||
        !("data" in message) ||
        !("type" in message)
      ) {
        return
      }

      if (message.type === "error") {
        const error = typeof message.data === "string" ? message.data : "Voice worker error"
        events.emit("error", { error: new Error(error) })
      } else if (message.type === "log" && message.data === "response_starting") {
        events.emit("mode_change", { mode: "thinking" })
      } else if (message.type === "log" && message.data === "started_talking") {
        events.emit("mode_change", { mode: "speaking" })
      }
    })

    return {
      async startAudioCapture() {
        if (!localStream) {
          localStream = await navigator.mediaDevices.getUserMedia({ audio: true })
          const [track] = localStream.getAudioTracks()
          if (!track) throw new Error("Microphone did not provide an audio track")
          await audioTransceiver.sender.replaceTrack(track)
        }
        localStream.getAudioTracks().forEach((track) => {
          track.enabled = true
        })
        events.emit("mode_change", { mode: "listening" })
      },

      stopAudioCapture() {
        localStream?.getAudioTracks().forEach((track) => {
          track.enabled = false
        })
      },

      sendText() {
        throw new Error("The worker-voice WebRTC contract does not support text input")
      },

      sendImage() {
        throw new Error("The worker-voice WebRTC contract does not support image input")
      },

      sendToolResult() {
        throw new Error("The worker-voice WebRTC contract does not support tool results")
      },

      updateSession() {
        // FastRTC exposes no session-update operation in the worker contract.
      },

      interrupt() {
        // FastRTC exposes no remote interruption operation in the worker contract.
      },

      on: events.on,
      getAudioVisualization: () => audioVisualization,

      async disconnect() {
        localStream?.getTracks().forEach((track) => track.stop())
        dataChannel.close()
        audio.pause()
        audio.srcObject = null
        peer.close()
        events.emit("status_change", { status: "idle" })
      },
    }
  },
}

export const getFastRtcToken = async (): Promise<RealtimeToken> => {
  const response = await fetch("/api/voice/session", {
    method: "POST",
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
  })
  if (!response.ok) throw new Error("Unable to start a voice session")

  const token: unknown = await response.json()
  if (
    typeof token !== "object" ||
    token === null ||
    !("provider" in token) ||
    token.provider !== "worker-voice" ||
    !("token" in token) ||
    typeof token.token !== "string" ||
    !("expiresAt" in token) ||
    typeof token.expiresAt !== "number" ||
    !("config" in token) ||
    typeof token.config !== "object" ||
    token.config === null ||
    !("providerOptions" in token.config) ||
    typeof token.config.providerOptions !== "object" ||
    token.config.providerOptions === null ||
    !("workerUrl" in token.config.providerOptions) ||
    typeof token.config.providerOptions.workerUrl !== "string" ||
    !("rtcConfiguration" in token.config.providerOptions)
  ) {
    throw new Error("Voice session route returned an invalid session")
  }

  const rtcConfiguration = readRtcConfiguration(
    token.config.providerOptions.rtcConfiguration,
  )
  return {
    provider: token.provider,
    token: token.token,
    expiresAt: token.expiresAt,
    config: {
      providerOptions: {
        workerUrl: token.config.providerOptions.workerUrl,
        rtcConfiguration,
      },
    },
  }
}
