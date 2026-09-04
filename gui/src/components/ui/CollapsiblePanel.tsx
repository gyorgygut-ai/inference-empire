"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible";

interface CollapsiblePanelProps {
  title: string;
  children: ReactNode;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  side?: "left" | "right";
  className?: string;
}

export function CollapsiblePanel({
  title,
  children,
  open,
  onOpenChange,
  side = "left",
  className,
}: CollapsiblePanelProps) {
  return (
    <Collapsible
      open={open}
      onOpenChange={onOpenChange}
      className={cn(
        "flex h-full w-[280px] shrink-0 flex-col overflow-hidden border-border bg-secondary",
        className,
      )}
    >
      <div className="flex h-10 shrink-0 items-center border-b border-border px-3">
        <span className="truncate text-sm font-medium text-foreground select-none">
          {title}
        </span>
      </div>
      <CollapsibleContent className="min-h-0 flex-1 overflow-y-auto px-4 py-3 text-sm text-muted-foreground">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}
