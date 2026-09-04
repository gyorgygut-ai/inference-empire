import { WorkersPanel } from "@/components/panels/WorkersPanel"
import { ArtifactsPanel } from "@/components/panels/ArtifactsPanel"
import { ChatPlaceholder } from "@/components/panels/ChatPlaceholder"

export function AppShell() {
  return (
    <div className="grid h-dvh grid-cols-1 md:grid-cols-[auto_1fr_auto]">
      <div className="hidden md:block md:border-r md:border-border">
        <WorkersPanel />
      </div>
      <ChatPlaceholder />
      <div className="hidden md:block md:border-l md:border-border">
        <ArtifactsPanel />
      </div>
    </div>
  )
}
