"use client"

import { useState } from "react"
import { Toggle } from "@inference/ui/components/Toggle"
import { vocabulary } from "@/messages"
import { RealtimeVoiceSession, type VoiceProvider } from "./RealtimeVoiceSession"

export const VoiceChatView = () => {
  const [provider, setProvider] = useState<VoiceProvider>("ELEVENLABS")

  return (
    <>
      <div className="absolute left-1/2 top-[calc(50%+10rem)] z-20 -translate-x-1/2">
        <Toggle
          label={vocabulary.provider.label}
          options={[
            { value: "ELEVENLABS", label: vocabulary.provider.elevenLabs },
            { value: "OPENAI", label: vocabulary.provider.openAi },
            { value: "VOICE_FASTRTC", label: vocabulary.provider.fastRtc },
          ]}
          value={provider}
          onValueChange={setProvider}
        />
      </div>
      <RealtimeVoiceSession key={provider} provider={provider} />
    </>
  )
}

export default VoiceChatView
