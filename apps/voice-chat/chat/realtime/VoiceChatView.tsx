import { vocabulary } from "@/messages"
import VoiceOrb from "@/chat/parts/voice-orb"

type VoiceChatViewProps = {
  connected: boolean
}

export const VoiceChatView = ({ connected }: VoiceChatViewProps) => (
  <div className="grid min-h-[calc(100svh-3rem)] w-full place-items-center">
    <VoiceOrb connected={connected} label={vocabulary.voice.orbLabel} />
  </div>
)

export default VoiceChatView
