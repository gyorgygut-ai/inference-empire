import clsx from "clsx"
import type { RealtimeMode, RealtimeStatus } from "@tanstack/ai"

type VoiceOrbProps = {
  status: RealtimeStatus
  mode: RealtimeMode
  label: string
}

export const VoiceOrb = ({ status, mode, label }: VoiceOrbProps) => (
  <div
    className={clsx(
      "relative grid aspect-square w-[min(45vw,14.7rem)] place-items-center rounded-full transition-[opacity,transform] duration-500 ease-in-out motion-reduce:transition-none",
      {
        "opacity-100": status === "connected",
        "opacity-70": status === "connecting" || status === "reconnecting",
        "opacity-20": status === "idle" || status === "error",
        "scale-110": mode === "speaking",
        "scale-100": mode !== "speaking",
      },
    )}
    role="img"
    aria-label={`${label}, ${status}, ${mode}`}
  >
    <span
      className="absolute inset-[-8%] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(191,52,78,0.22)_0%,rgba(37,123,210,0.16)_42%,transparent_72%)] blur-2xl animate-pulse"
      aria-hidden="true"
    />
    <span
      className="absolute inset-[8%] rounded-full bg-[linear-gradient(115deg,#081c49_0%,#1450a0_17%,#257bd2_36%,#6659a8_51%,#bf344e_68%,#e6a53c_86%,#ffdc77_100%)] opacity-60 blur-xl animate-pulse"
      aria-hidden="true"
    />
    <span
      className={clsx(
        "absolute inset-[7%] rounded-full bg-[conic-gradient(from_0deg,transparent_0deg,rgba(255,255,255,1)_18deg,rgba(255,220,119,1)_32deg,transparent_55deg,transparent_180deg,rgba(37,123,210,1)_215deg,transparent_250deg)] drop-shadow-[0_0_8px_rgba(255,220,119,0.7)] animate-spin",
        {
          "[animation-duration:1.5s]": mode === "thinking",
          "[animation-duration:36s]": mode === "listening",
          "[animation-duration:12s]":
            mode !== "thinking" && mode !== "listening",
          "drop-shadow-[0_0_16px_rgba(255,220,119,1)]":
            mode === "thinking",
        },
      )}
      aria-hidden="true"
    />
    <span
      className="absolute inset-[10%] rounded-full bg-[linear-gradient(115deg,#081c49_0%,#1450a0_17%,#257bd2_36%,#6659a8_51%,#bf344e_68%,#e6a53c_86%,#ffdc77_100%)] shadow-2xl shadow-primary/30"
      aria-hidden="true"
    />
    <span
      className="absolute inset-[10%] rounded-full bg-[radial-gradient(ellipse_at_30%_24%,rgba(255,255,255,0.58),transparent_38%)]"
      aria-hidden="true"
    />
  </div>
)

export default VoiceOrb
