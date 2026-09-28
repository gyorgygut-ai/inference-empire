import fs from "fs"
import path from "path"
import matter from "gray-matter"
import type { Flux2Klein9BInput } from "@/app/inference-api/schema"

export type Outcome = Pick<Flux2Klein9BInput, "prompt" | "width" | "height"> & {
  id: string
  title: string
  order: number
}

const outcomesDir = path.join(process.cwd(), "outcomes")

const outcomeCache = new Map<string, Outcome>(
  fs.readdirSync(outcomesDir)
    .filter((f) => f.endsWith(".md"))
    .map((file) => {
      const { data, content } = matter(fs.readFileSync(path.join(outcomesDir, file), "utf-8"))
      const outcome: Outcome = {
        id: data.id as string,
        title: data.title as string,
        order: data.order as number,
        prompt: content.trim(),
        height: data.height as number,
        width: data.width as number,
      }
      return [outcome.id, outcome]
    })
)

export type PublicOutcome = {
  id: string
  title: string
  width: number
  height: number
}

export function getPublicOutcomes(): PublicOutcome[] {
  return Array.from(outcomeCache.values())
    .sort((a, b) => a.order - b.order)
    .map(({ id, title, width, height }) => ({ id, title, width: width ?? 512, height: height ?? 768 }))
}

export function getInferenceOutcome(id: string): Outcome | null {
  return outcomeCache.get(id) ?? null
}
