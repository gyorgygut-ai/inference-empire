"use client"

import { PanelLeft, PanelRight } from "lucide-react"
import { Thread } from "@/components/assistant-ui/thread"
import { useChatContext } from "@/components/runtime/RuntimeProvider"
import type { ModelGroup } from "@/lib/chat/directHandlers"

interface MainProps {
  onToggleLeft: () => void
  onToggleRight: () => void
}

const GROUPS: ModelGroup[] = ["vision", "flux", "krea", "h3", "h3-ref"]

export function Main({ onToggleLeft, onToggleRight }: MainProps) {
  const { group, setGroup, boxes, setBoxes, setImageBase64 } = useChatContext()

  function updateBox(k: string, v: unknown) {
    setBoxes({ ...boxes, [k]: v })
  }

  return (
    <section className="flex h-full min-h-0 flex-col bg-background">
      <header className="flex h-10 shrink-0 items-center justify-between border-b border-border px-3">
        <button
          type="button"
          aria-label="Toggle Workers"
          onClick={onToggleLeft}
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <PanelLeft className="h-4 w-4" />
        </button>
        <div className="flex items-center gap-2">
          <select
            value={group}
            onChange={(e) => setGroup(e.target.value as ModelGroup)}
            className="rounded border border-input bg-background px-2 py-1 text-sm"
          >
            {GROUPS.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </div>
        <button
          type="button"
          aria-label="Toggle Artifacts"
          onClick={onToggleRight}
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <PanelRight className="h-4 w-4" />
        </button>
      </header>

      {group === "vision" ? (
        <div className="border-b border-border p-2">
          <label className="text-xs text-muted-foreground">Image attachment</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (!file) return setImageBase64(null)
              const reader = new FileReader()
              reader.onload = () => setImageBase64(String(reader.result).split(",")[1])
              reader.readAsDataURL(file)
            }}
            className="mt-1 block text-xs"
          />
        </div>
      ) : null}

      {group === "flux" ? (
        <>
          <Boxes
            fields={[
              ["height", 512],
              ["width", 512],
              ["guidance_scale", 1],
              ["num_inference_steps", 4],
              ["seed", ""],
            ]}
            boxes={boxes}
            updateBox={updateBox}
          />
          <div className="flex flex-wrap gap-2 border-b border-border p-2">
            <label className="text-xs text-muted-foreground">reference_images</label>
            <input type="file" accept="image/*" multiple onChange={(e) => { const files = Array.from(e.target.files ?? []); const dataUrls = files.map(f => URL.createObjectURL(f)); updateBox("reference_images", dataUrls) }} className="text-xs" />
            <label className="text-xs text-muted-foreground">input_image</label>
            <input type="file" accept="image/*" onChange={(e) => { const file = e.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => updateBox("input_image", String(reader.result).split(",")[1]); reader.readAsDataURL(file) }} className="text-xs" />
          </div>
        </>
      ) : null}

      {group === "krea" ? (
        <>
          <Boxes
            fields={[
              ["height", 768],
              ["width", 768],
              ["num_inference_steps", 8],
              ["guidance_scale", 0],
              ["seed", ""],
              ["lora_scale", 1],
              ["face_crop", true],
            ]}
            boxes={boxes}
            updateBox={updateBox}
          />
          <div className="flex flex-wrap gap-2 border-b border-border p-2">
            <label className="text-xs text-muted-foreground">reference_image</label>
            <input type="file" accept="image/*" onChange={(e) => { const file = e.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => updateBox("reference_image", String(reader.result).split(",")[1]); reader.readAsDataURL(file) }} className="text-xs" />
          </div>
        </>
      ) : null}

      {group === "h3" ? (
        <>
          <Boxes
            fields={[
              ["width", 1344],
              ["height", 768],
              ["length", 124],
              ["steps", 4],
              ["seed", ""],
              ["first_frame", ""],
              ["last_frame", ""],
            ]}
            boxes={boxes}
            updateBox={updateBox}
          />
          <div className="flex flex-wrap gap-2 border-b border-border p-2">
            <label className="text-xs text-muted-foreground">variant</label>
            <select value={String(boxes.h3_variant ?? "fl2va")} onChange={e=>updateBox("h3_variant", e.target.value)} className="text-xs rounded border px-1 py-0.5">
              <option value="fl2va">fl2va</option>
              <option value="comfy">comfy</option>
            </select>
          </div>
        </>
      ) : null}

      {group === "h3-ref" ? (
        <>
          <Boxes
            fields={[
              ["width", 960],
              ["height", 544],
              ["length", 124],
              ["steps", 4],
              ["seed", ""],
            ]}
            boxes={boxes}
            updateBox={updateBox}
          />
          <div className="flex flex-wrap gap-2 border-b border-border p-2">
            <label className="text-xs text-muted-foreground">ref_images (≤9)</label>
            <input type="file" accept="image/*" multiple onChange={(e) => { const files = Array.from(e.target.files ?? []).slice(0,9); const dataUrls = files.map(f => URL.createObjectURL(f)); updateBox("ref_images", dataUrls) }} className="text-xs" />
            <label className="text-xs text-muted-foreground">ref_videos (≤3)</label>
            <input type="file" accept="video/*" multiple onChange={(e) => { const files = Array.from(e.target.files ?? []).slice(0,3); const dataUrls = files.map(f => URL.createObjectURL(f)); updateBox("ref_videos", dataUrls) }} className="text-xs" />
            <label className="text-xs text-muted-foreground">ref_video_audios (≤3)</label>
            <input type="file" accept="audio/*" multiple onChange={(e) => { const files = Array.from(e.target.files ?? []).slice(0,3); const dataUrls = files.map(f => URL.createObjectURL(f)); updateBox("ref_video_audios", dataUrls) }} className="text-xs" />
            <label className="text-xs text-muted-foreground">ref_audios (≤3)</label>
            <input type="file" accept="audio/*" multiple onChange={(e) => { const files = Array.from(e.target.files ?? []).slice(0,3); const dataUrls = files.map(f => URL.createObjectURL(f)); updateBox("ref_audios", dataUrls) }} className="text-xs" />
          </div>
        </>
      ) : null}

      <div className="min-h-0 flex-1">
        <Thread />
      </div>
    </section>
  )
}

function Boxes({
  fields,
  boxes,
  updateBox,
}: {
  fields: [string, unknown][]
  boxes: Record<string, unknown>
  updateBox: (k: string, v: unknown) => void
}) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-border p-2">
      {fields.map(([k, def]) => (
        <label key={k} className="flex flex-col text-xs">
          <span className="text-muted-foreground">{k}</span>
          <input
            value={String(boxes[k] ?? def ?? "")}
            onChange={(e) => {
              const v = e.target.value
              if (typeof def === "number") updateBox(k, v === "" ? "" : Number(v))
              else if (typeof def === "boolean") updateBox(k, v === "true" || v === "1")
              else updateBox(k, v)
            }}
            className="w-20 rounded border border-input px-2 py-1 text-sm"
          />
        </label>
      ))}
    </div>
  )
}
