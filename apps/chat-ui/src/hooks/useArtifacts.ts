"use client"

import { useAuiState } from "@assistant-ui/react"
import type { Artifact } from "@/lib/artifacts/types"

type Part = { type: string; image?: string; src?: string; file?: string; data?: string; filename?: string; model?: string }

export function useArtifacts(): Artifact[] {
  const messages = useAuiState((s) => s.thread.messages as unknown as { parts?: Part[]; model?: string }[])

  const artifacts: Artifact[] = []
  let id = 0

  for (const msg of messages ?? []) {
    const parts = (msg as { parts?: Part[] }).parts ?? []
    for (const part of parts) {
      if (part.type !== "image" && part.type !== "file") continue
      const url = part.image ?? part.src ?? part.file ?? part.data
      if (!url || typeof url !== "string" || !url.startsWith("http")) continue

      const isVideo = url.match(/\.(mp4|webm|mov)(\?|$)/i)
      artifacts.push({
        id: String(id++),
        presigned_url: url,
        kind: isVideo ? "video" : "image",
      })
    }
  }

  return artifacts
}
