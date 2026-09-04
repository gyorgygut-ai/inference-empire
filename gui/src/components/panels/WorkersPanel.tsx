import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel"

interface WorkersPanelProps {
  defaultOpen?: boolean
}

export function WorkersPanel({ defaultOpen }: WorkersPanelProps) {
  return (
    <CollapsiblePanel title="Workers" defaultOpen={defaultOpen}>
      Workers
    </CollapsiblePanel>
  )
}
