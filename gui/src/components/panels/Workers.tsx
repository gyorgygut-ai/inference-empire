import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel";
import { PanelLeft } from "lucide-react";

interface WorkersProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function Workers({ open, onOpenChange }: WorkersProps) {
  return (
    <CollapsiblePanel
      title="Workers"
      side="left"
      open={open}
      onOpenChange={onOpenChange}
      buttonIcon={<PanelLeft className="h-4 w-4" />}
    >
      Workers todo
    </CollapsiblePanel>
  );
}
