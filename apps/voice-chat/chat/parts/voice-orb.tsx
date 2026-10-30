type VoiceOrbProps = {
  connected: boolean
  label: string
}

export const VoiceOrb = ({ connected, label }: VoiceOrbProps) => (
  <div
    className={`relative grid aspect-square w-[min(68vw,22rem)] place-items-center rounded-full transition-opacity duration-500 ${
      connected ? "opacity-100" : "opacity-20"
    }`}
    role="img"
    aria-label={`${label}, ${connected ? "connected" : "disconnected"}`}
  >
    <span
      className="absolute inset-[3%] rounded-full bg-primary/10 blur-2xl"
      aria-hidden="true"
    />
    <span
      className="absolute inset-[15%] rounded-full bg-gradient-to-br from-white via-primary to-accent shadow-2xl shadow-primary/30"
      aria-hidden="true"
    />
    <span
      className="absolute inset-[18%_24%_52%] rounded-full bg-gradient-to-b from-white/70 to-transparent blur-md"
      aria-hidden="true"
    />
  </div>
)

export default VoiceOrb
