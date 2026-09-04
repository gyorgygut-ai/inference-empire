import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel"

interface WorkersProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function Workers({ open, onOpenChange }: WorkersProps) {
  return (
    <CollapsiblePanel title="Workers" side="left" open={open} onOpenChange={onOpenChange}>
      Workers
    </CollapsiblePanel>
  )
}
