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

const outcomesDir = path.join(process.cwd(), "outcomes")

const outcomeCache = new Map<string, Outcome>(
  fs
    .readdirSync(outcomesDir)
    .filter((f) => f.endsWith(".md"))
    .map((file) => {
      const { data, content } = matter(fs.readFileSync(path.join(outcomesDir, file), "utf-8"))
      const outcome: Outcome = {
        id: typeof data.id === 'string' ? data.id : '',
        title: typeof data.title === 'string' ? data.title : '',
        order: typeof data.order === 'number' ? data.order : 0,
        prompt: content.trim(),
        height: typeof data.height === 'number' ? data.height : 768,
        width: typeof data.width === 'number' ? data.width : 512,
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