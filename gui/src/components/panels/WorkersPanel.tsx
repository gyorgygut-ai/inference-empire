import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel"

interface WorkersPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WorkersPanel({ open, onOpenChange }: WorkersPanelProps) {
  return (
    <CollapsiblePanel title="Workers" side="left" open={open} onOpenChange={onOpenChange}>
      Workers
    </CollapsiblePanel>
  )
}
