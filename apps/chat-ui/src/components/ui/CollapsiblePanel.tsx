"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

type CollapsibleProps = React.ComponentProps<typeof Collapsible>;

interface CollapsiblePanelProps extends CollapsibleProps {
  title: string;
  children: ReactNode;
  buttonIcon?: ReactNode;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  side?: "left" | "right";
  forceMountContent?: React.ComponentProps<
    typeof CollapsibleContent
  >["forceMount"];
}

export function CollapsiblePanel({
  title,
  children,
  className,
  buttonIcon,
  forceMountContent,
  ...props
}: CollapsiblePanelProps) {
  return (
    <Collapsible {...props}>
      <CollapsibleContent
        forceMount={forceMountContent}
        className={cn(
          className,
          "min-h-0 h-full flex-1 overflow-y-auto text-sm text-muted-foreground bg-secondary",
        )}
      >
        <div className="flex justify-between w-100 h-10 shrink-0 items-center border-b border-border px-3">
          <span className="truncate text-sm font-medium text-foreground select-none">
            {title}
          </span>
          <CollapsibleTrigger>{buttonIcon}</CollapsibleTrigger>
        </div>
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}
