"use client"

import type { ReactNode } from "react"
import { cn } from "@/lib/utils"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

interface CollapsiblePanelProps {
  title: string
  children: ReactNode
  defaultOpen?: boolean
  className?: string
}

export function CollapsiblePanel({
  title,
  children,
  defaultOpen = true,
  className,
}: CollapsiblePanelProps) {
  return (
    <Collapsible
      defaultOpen={defaultOpen}
      className={cn("flex h-full min-h-0 flex-col bg-background", className)}
    >
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="flex h-10 shrink-0 items-center px-4 text-sm font-medium text-foreground outline-none select-none data-[state=open]:border-b data-[state=open]:border-border"
        >
          {title}
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="min-h-0 flex-1 overflow-y-auto px-4 py-3 text-sm text-muted-foreground">
        {children}
      </CollapsibleContent>
    </Collapsible>
  )
}
