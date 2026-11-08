"use client"

import { startTransition, useOptimistic, useRef, useState } from "react"
import { useRealtimeChat } from "@tanstack/ai-react"
import type { RealtimeStatus } from "@tanstack/ai"
import { openaiRealtime } from "@tanstack/ai-openai"
import { Draggable } from "@inference/ui/components/Draggable"
import { Toggle } from "@inference/ui/components/Toggle"
import { Toast } from "@inference/ui/components/Toast"
import { useMessageQueue } from "@inference/ui/hooks/useMessageQueue"
import { vocabulary } from "@/messages"
import VoiceOrb from "@/chat/parts/voice-orb"
import { fastRtcAdapter, getFastRtcToken } from "./fastRtcAdapter"

type Provider = "workers" | "openai"

const isActiveStatus = (status: RealtimeStatus) =>
  status === "connected" || status === "connecting" || status === "reconnecting"

export const VoiceChatView = () => {
  const [provider, setProvider] = useState<Provider>("workers")

  const { messages, addMessage, removeMessage } = useMessageQueue()

  const { status, mode, connect, disconnect } = useRealtimeChat({
    adapter: provider === "openai" ? openaiRealtime() : fastRtcAdapter,
    getToken: provider === "openai" ? getOpenAiToken : getFastRtcToken,
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
            addMessage("Voice worker request failed")
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
      <div className="absolute left-1/2 top-[calc(50%+10rem)] z-20 -translate-x-1/2">
        <Toggle
          label="Voice provider"
          options={[{ value: "workers", label: "Workers" }, { value: "openai", label: "OpenAI" }]}
          value={provider}
          onValueChange={(nextProvider) => {
            setProvider(nextProvider)
          }}
        />
      </div>
      <Toast messages={messages} onRemove={removeMessage} />
    </>
  )
}

const getOpenAiToken = async () => {
  const response = await fetch("/api/voice/openai-session", { method: "POST", cache: "no-store" })
  if (!response.ok) throw new Error("Unable to start an OpenAI voice session")
  return response.json()
}

export default VoiceChatView
