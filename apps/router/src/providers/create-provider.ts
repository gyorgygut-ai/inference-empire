import { beamProvider } from './provider-beam'
import { flashProvider } from './provider-flash'

export const enum Status {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  REJECTED = 'rejected'
}

export interface BeamConfig {
  url: string
  taskApi: string
}

export interface FlashConfig {
  url: string
  endpointName: string
}

export interface ProviderConfigs {
  beam: BeamConfig
  flash: FlashConfig
}

export type ProviderName = keyof ProviderConfigs

export interface Provider<K extends ProviderName> {
  encodeTaskId(originalTaskId: string): string
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string }
  pushToTaskQueue(input: Record<string, unknown>, config: ProviderConfigs[K]): Promise<{ task_id: string }>
  fetchTaskStatus(taskId: string, config: ProviderConfigs[K]): Promise<{ status: Status; output?: unknown }>
}

const providers: { [K in ProviderName]: Provider<K> } = {
  beam: beamProvider,
  flash: flashProvider
}

export function isProviderName(value: string): value is ProviderName {
  return value === 'beam' || value === 'flash'
}

export default function createProvider<K extends ProviderName>(name: K): Provider<K> {
  return providers[name]
}
