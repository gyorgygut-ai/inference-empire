import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel"

interface ArtifactsPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ArtifactsPanel({ open, onOpenChange }: ArtifactsPanelProps) {
  return (
    <CollapsiblePanel title="Artifacts" side="right" open={open} onOpenChange={onOpenChange}>
      Artifacts
    </CollapsiblePanel>
  )
}
