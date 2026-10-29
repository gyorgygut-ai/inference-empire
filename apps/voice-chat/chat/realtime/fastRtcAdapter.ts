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

const readIceServers = (value: unknown): Array<RTCIceServer> => {
  if (typeof value !== "object" || value === null || !("iceServers" in value)) {
    throw new Error("Voice worker returned invalid ICE configuration")
  }

  const { iceServers } = value
  if (!Array.isArray(iceServers)) {
    throw new Error("Voice worker returned invalid ICE configuration")
  }

  return iceServers.map((server: unknown) => {
    if (typeof server !== "object" || server === null || !("urls" in server)) {
      throw new Error("Voice worker returned invalid ICE server")
    }

    const { urls } = server
    if (
      typeof urls !== "string" &&
      !(Array.isArray(urls) && urls.every((url) => typeof url === "string"))
    ) {
      throw new Error("Voice worker returned invalid ICE server URLs")
    }

    const iceServer: RTCIceServer = { urls }
    if ("username" in server && typeof server.username === "string") {
      iceServer.username = server.username
    }
    if ("credential" in server && typeof server.credential === "string") {
      iceServer.credential = server.credential
    }
    return iceServer
  })
}

const readSessionDescription = (value: unknown): RTCSessionDescriptionInit => {
  if (
    typeof value !== "object" ||
    value === null ||
    !("sdp" in value) ||
    typeof value.sdp !== "string" ||
    !("type" in value) ||
    value.type !== "answer"
  ) {
    throw new Error("Voice worker returned an invalid WebRTC answer")
  }

  return { sdp: value.sdp, type: "answer" }
}

const fetchIceServers = async () => {
  const response = await fetch("/api/voice/rtc-configuration", { cache: "no-store" })
  if (!response.ok) throw new Error("Unable to retrieve voice connection configuration")
  return readIceServers(await response.json())
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

const connectFastRtc = async (sessionId: string) => {
  const peer = new RTCPeerConnection({ iceServers: await fetchIceServers() })
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

    const response = await fetch("/api/voice/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sdp: localDescription.sdp,
        type: localDescription.type,
        webrtc_id: sessionId,
      }),
    })

    const answer: unknown = await response.json()
    if (!response.ok) throw new Error("Voice worker rejected the WebRTC offer")
    await peer.setRemoteDescription(readSessionDescription(answer))
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
  provider: "workers-voice",

  async connect(token: RealtimeToken) {
    const { peer, audioTransceiver, dataChannel, audio } = await connectFastRtc(token.token)
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
      },

      stopAudioCapture() {
        localStream?.getAudioTracks().forEach((track) => {
          track.enabled = false
        })
      },

      sendText() {
        throw new Error("The workers-voice WebRTC contract does not support text input")
      },

      sendImage() {
        throw new Error("The workers-voice WebRTC contract does not support image input")
      },

      sendToolResult() {
        throw new Error("The workers-voice WebRTC contract does not support tool results")
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
  })
  if (!response.ok) throw new Error("Unable to start a voice session")

  const token: unknown = await response.json()
  if (
    typeof token !== "object" ||
    token === null ||
    !("provider" in token) ||
    token.provider !== "workers-voice" ||
    !("token" in token) ||
    typeof token.token !== "string" ||
    !("expiresAt" in token) ||
    typeof token.expiresAt !== "number"
  ) {
    throw new Error("Voice session route returned an invalid session")
  }

  return {
    provider: token.provider,
    token: token.token,
    expiresAt: token.expiresAt,
    config: {},
  }
}
