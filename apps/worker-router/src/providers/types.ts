import type { ProviderName } from "../task-id"
import type { RouterInput } from "../contracts"

export type TaskStatus = "BUSY" | "REJECTED" | "DONE"

export interface TaskResult {
  status: TaskStatus
  output?: unknown
}

export interface Provider {
  name: ProviderName
  queue(input: RouterInput): Promise<string>
  status(id: string): Promise<TaskResult>
}
