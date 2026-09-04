import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel"

interface ArtifactsProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  className?: string
}

export function Artifacts({ open, onOpenChange, className }: ArtifactsProps) {
  return (
    <CollapsiblePanel title="Artifacts" side="right" open={open} onOpenChange={onOpenChange} className={className}>
      Artifacts
    </CollapsiblePanel>
  )
}
