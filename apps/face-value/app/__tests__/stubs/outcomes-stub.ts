export interface OutcomeInput {
  prompt: string
  width?: number
  height?: number
}

export function createOutcomeStub(map: Record<string, OutcomeInput | null>) {
  return (id: string) => map[id]
}
