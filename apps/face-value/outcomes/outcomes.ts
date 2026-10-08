import outcomesData from "./outcomes.json";

export type Outcome = {
  id: string;
  title: string;
  order: number;
  width: number;
  height: number;
  prompt: string;
};

const outcomeCache = new Map<string, Outcome>(
  outcomesData.map((o) => [o.id, o as Outcome])
);

export type PublicOutcome = {
  id: string;
  title: string;
  width: number;
  height: number;
};

export function getPublicOutcomes(): PublicOutcome[] {
  return Array.from(outcomeCache.values())
    .sort((a, b) => a.order - b.order)
    .map(({ id, title, width, height }) => ({ id, title, width: width ?? 512, height: height ?? 768 }));
}

export function getInferenceOutcome(id: string): Outcome | null {
  return outcomeCache.get(id) ?? null;
}
