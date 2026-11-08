"use client"

import { startTransition, useOptimistic, useRef } from "react"
import type { RealtimeStatus } from "@tanstack/ai"
import { useRealtimeChat } from "@tanstack/ai-react"
import { elevenlabsRealtime } from "@tanstack/ai-elevenlabs"
import { openaiRealtime } from "@tanstack/ai-openai"
import { Draggable } from "@inference/ui/components/Draggable"
import { Toast } from "@inference/ui/components/Toast"
import { useMessageQueue } from "@inference/ui/hooks/useMessageQueue"
import { vocabulary } from "@/messages"
import VoiceOrb from "@/chat/parts/voice-orb"
import { fastRtcAdapter, getFastRtcToken } from "./fastRtcAdapter"

export type VoiceProvider = "VOICE_FASTRTC" | "OPENAI" | "ELEVENLABS"

const isActiveStatus = (status: RealtimeStatus) =>
  status === "connected" || status === "connecting" || status === "reconnecting"

export const RealtimeVoiceSession = ({ provider }: { provider: VoiceProvider }) => {
  const { messages, addMessage, removeMessage } = useMessageQueue()
  const { status, mode, connect, disconnect } = useRealtimeChat({
    adapter: provider === "OPENAI"
      ? openaiRealtime()
      : provider === "ELEVENLABS"
        ? elevenlabsRealtime()
        : fastRtcAdapter,
    getToken: provider === "OPENAI"
      ? getOpenAiToken
      : provider === "ELEVENLABS"
        ? getElevenLabsToken
        : getFastRtcToken,
  })
  const [displayStatus, setDisplayStatus] = useOptimistic(status)
  const connectionQueue = useRef<Promise<void>>(Promise.resolve())

  const toggleConnection = () => {
    const nextStatus = isActiveStatus(displayStatus) ? "idle" : "connecting"

    startTransition(async () => {
      setDisplayStatus(nextStatus)
      connectionQueue.current = connectionQueue.current
        .then(() => nextStatus === "idle" ? disconnect() : connect())
        .catch((error: unknown) => {
          if (error instanceof Error) {
            addMessage(error.message)
          } else {
            addMessage("Voice session request failed")
          }
        })
      await connectionQueue.current
    })
  }

  return (
    <>
      <Draggable
        label={vocabulary.voice.dragHandleLabel}
        pressed={isActiveStatus(displayStatus)}
        onClick={toggleConnection}
        initialPosition={{ x: 0, y: 48 }}
      >
        <VoiceOrb status={displayStatus} mode={mode} label={vocabulary.voice.orbLabel} />
      </Draggable>
      <Toast messages={messages} onRemove={removeMessage} />
    </>
  )
}

const getOpenAiToken = async () => {
  const response = await fetch("/api/voice/openai-session", { method: "POST", cache: "no-store" })
  if (!response.ok) throw new Error("Unable to start an OpenAI voice session")
  return response.json()
}

const getElevenLabsToken = async () => {
  const response = await fetch("/api/voice/elevenlabs-session", {
    method: "POST",
    cache: "no-store",
  })
  if (!response.ok) throw new Error("Unable to start an ElevenLabs voice session")
  return response.json()
}
