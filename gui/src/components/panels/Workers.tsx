"use client"

import { useEffect, useState } from "react"
import { PanelLeft } from "lucide-react"
import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import manifest from "@/lib/manifest.json"

interface WorkersProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Status = "unknown" | "healthy" | "unhealthy" | "deployed"

const GROUP_ORDER = ["vision", "flux2", "krea2", "h3", "voice"] as const

function getGroup(model: string): string {
  if (model === "small_vision") return "vision"
  if (model === "flux2_klein9b") return "flux2"
  if (model === "krea2_ref2img") return "krea2"
  if (model.startsWith("minimax_h3")) return "h3"
  return "voice"
}

function StatusDot({ status }: { status: Status }) {
  const color =
    status === "healthy"
      ? "bg-green-500"
      : status === "unhealthy"
        ? "bg-red-500"
        : status === "deployed"
          ? "bg-yellow-500"
          : "bg-gray-400"
  return <span className={`h-2 w-2 rounded-full ${color}`} aria-label={status} />
}

export function Workers({ open, onOpenChange }: WorkersProps) {
  const [statusMap, setStatusMap] = useState<Record<string, Status>>({})

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const res = await fetch("/api/workers/status")
        if (!res.ok) return
        const data = await res.json()
        if (cancelled) return
        const map: Record<string, Status> = {}
        for (const w of data.workers ?? []) map[w.stem] = w.status
        setStatusMap(map)
      } catch {
        return
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const grouped: Record<string, typeof manifest.workers> = {}
  for (const g of GROUP_ORDER) grouped[g] = []
  for (const w of manifest.workers) {
    const g = getGroup(w.model)
    if (!grouped[g]) grouped[g] = []
    grouped[g].push(w)
  }

  const modelGroups: Record<string, Record<string, typeof manifest.workers>> = {}
  for (const g of GROUP_ORDER) {
    const byModel: Record<string, typeof manifest.workers> = {}
    for (const w of grouped[g] ?? []) {
      if (!byModel[w.model]) byModel[w.model] = []
      byModel[w.model].push(w)
    }
    modelGroups[g] = byModel
  }

  return (
    <CollapsiblePanel
      title="Workers"
      side="left"
      open={open}
      onOpenChange={onOpenChange}
      buttonIcon={<PanelLeft className="h-4 w-4" />}
    >
      <div className="flex flex-col gap-2 p-2">
        {GROUP_ORDER.map((group) => {
          const workers = grouped[group] ?? []
          if (workers.length === 0) return null
          const byModel = modelGroups[group] ?? {}
          return (
            <Collapsible key={group} defaultOpen={group === "h3" || group === "flux2"}>
              <CollapsibleTrigger className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-xs font-medium text-foreground hover:bg-muted">
                <span>{group}</span>
                <span className="text-muted-foreground">{workers.length}</span>
              </CollapsibleTrigger>
              <CollapsibleContent className="flex flex-col gap-3 px-2 py-2">
                {Object.entries(byModel).map(([model, variants]) => (
                  <div key={model} className="flex flex-col gap-1">
                    <span className="text-xs font-medium text-foreground">{model}</span>
                    {variants.map((v) => (
                      <div
                        key={v.stem}
                        className="flex items-center justify-between rounded border border-border px-2 py-1"
                      >
                        <span className="truncate text-xs text-muted-foreground">{v.stem}</span>
                        <span className="flex items-center gap-2">
                          <span className="rounded border border-border px-1 py-0.5 text-[10px] text-muted-foreground">
                            {v.platform}/{v.pattern}
                          </span>
                          <StatusDot status={statusMap[v.stem] ?? "unknown"} />
                        </span>
                      </div>
                    ))}
                  </div>
                ))}
              </CollapsibleContent>
            </Collapsible>
          )
        })}
      </div>
    </CollapsiblePanel>
  )
}
