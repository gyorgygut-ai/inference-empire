import { modalProvider } from './provider-modal'
import { beamProvider } from './provider-beam'
import { flashProvider } from './provider-flash'

export const enum Status {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface Provider {
  encodeTaskId(originalTaskId: string): string
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string }
  pushToTaskQueue(prompt: string): Promise<{ task_id: string }>
  fetchTaskStatus(taskId: string): Promise<{ status: Status; output?: unknown }>
  mapTaskStatusToResponse(providerStatus: string): Status
}

const providers: Record<string, Provider> = {
  modal: modalProvider,
  beam: beamProvider,
  flash: flashProvider
}

export default function createProvider({ name }: { name: string }): Provider {
  const p = providers[name]
  if (!p) {
    throw new Error(`Unknown provider: ${name}`)
  }
  return p
}
