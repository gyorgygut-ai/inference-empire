"use client"

import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel"
import { PanelRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { useArtifacts } from "@/hooks/useArtifacts"

interface ArtifactsProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  className?: string
}

export function Artifacts({ open, onOpenChange, className }: ArtifactsProps) {
  const artifacts = useArtifacts()

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
      {artifacts.length === 0 ? (
        <div className="p-4 text-sm text-muted-foreground">No artifacts yet</div>
      ) : (
        <div className="grid grid-cols-2 gap-2 p-2">
          {artifacts.map((a) => (
            <div key={a.id} className="rounded border border-border p-1">
              {a.kind === "image" ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={a.presigned_url} alt="artifact" className="max-h-40 w-full rounded object-cover" />
              ) : (
                <video src={a.presigned_url} controls className="max-h-40 w-full rounded" />
              )}
              <div className="mt-1 flex gap-1">
                <a href={a.presigned_url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary underline">open</a>
                <a href={a.presigned_url} download className="text-xs text-primary underline">download</a>
              </div>
            </div>
          ))}
        </div>
      )}
    </CollapsiblePanel>
  )
}
