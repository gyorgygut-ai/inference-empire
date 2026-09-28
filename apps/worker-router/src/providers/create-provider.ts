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

export interface Env {
  MODAL_API_URL: string
  MODAL_TOKEN: string
  BEAM_API_URL: string
  BEAM_TOKEN: string
  FLASH_API_URL: string
  FLASH_TOKEN: string
  AUTH_TOKEN: string
}

export interface Provider {
  encodeTaskId(originalTaskId: string): string
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string }
  pushToTaskQueue(prompt: string, env: Env): Promise<{ task_id: string }>
  fetchTaskStatus(taskId: string, env: Env): Promise<{ status: Status; output?: unknown }>
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
