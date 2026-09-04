import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel"

interface ArtifactsPanelProps {
  defaultOpen?: boolean
}

export function ArtifactsPanel({ defaultOpen }: ArtifactsPanelProps) {
  return (
    <CollapsiblePanel title="Artifacts" defaultOpen={defaultOpen}>
      Artifacts
    </CollapsiblePanel>
  )
}
