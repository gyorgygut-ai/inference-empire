import type { GenerateResult, RunAction } from "../../chat-adapter"

export interface CallCounter {
  count: number;
}

export function createRunActionStub(result: GenerateResult, counter?: CallCounter): RunAction {
  return () => {
    if (counter) {
      counter.count += 1
    }
    return Promise.resolve(result)
  }
}
