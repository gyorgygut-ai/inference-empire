import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel";
import { PanelRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface ArtifactsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  className?: string;
}

export function Artifacts({ open, onOpenChange, className }: ArtifactsProps) {
  return (
    <CollapsiblePanel
      open={open}
      side="right"
      title="Artifacts"
      forceMountContent
      onOpenChange={onOpenChange}
      buttonIcon={<PanelRight className="h-4 w-4" />}
      className={cn(className, "hidden data-[state=open]:block lg:block")}
    >
      Artifacts todo
    </CollapsiblePanel>
  );
}
