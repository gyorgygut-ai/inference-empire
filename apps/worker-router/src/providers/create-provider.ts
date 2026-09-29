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
  AUTH_TOKEN: string
  PROVIDER_TYPE: 'modal' | 'beam' | 'flash'
  PROVIDER_API_URL: string
  PROVIDER_TOKEN: string
  PROVIDER_APP_NAME?: string
  PROVIDER_ENDPOINT_NAME?: string
  BEAM_API_URL?: string
  BEAM_TASK_API?: string
}

export interface Provider {
  encodeTaskId(originalTaskId: string): string
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string }
  pushToTaskQueue(input: Record<string, unknown>, env: Env): Promise<{ task_id: string }>
  fetchTaskStatus(taskId: string, env: Env): Promise<{ status: Status; output?: unknown }>
}

const providers: Record<string, Provider> = {
  modal: modalProvider,
  beam: beamProvider,
  flash: flashProvider
}

export default function createProvider({ provider, appName, endpointName }: { provider: string; appName?: string; endpointName?: string }): Provider {
  const p = providers[provider]
  if (!p) {
    throw new Error(`Unknown provider: ${provider}`)
  }
  return p
}
