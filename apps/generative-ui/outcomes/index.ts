import "server-only"
import fs from "fs"
import path from "path"
import matter from "gray-matter"

export type Outcome = {
  id: string;
  title: string;
  order: number;
  width: number;
  height: number;
  prompt: string;
}

export type PublicOutcome = {
  id: string;
  title: string;
  order: number;
  width: number;
  height: number;
}

const outcomesDir = path.join(process.cwd(), "targets/face-value/outcomes")

const outcomeCache = new Map<string, Outcome>(
  fs
    .readdirSync(outcomesDir)
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
    }),
)

export function getPublicOutcomes(): PublicOutcome[] {
  return Array.from(outcomeCache.values())
    .sort((a, b) => a.order - b.order)
    .map(({ id, title, order, width, height }) => ({
      id,
      title,
      order,
      width: width ?? 512,
      height: height ?? 768,
    }))
}

export function getInferenceOutcome(id: string): Outcome | null {
  return outcomeCache.get(id) ?? null
}
