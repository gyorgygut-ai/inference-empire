import { beamProvider } from './provider-beam'
import { flashProvider } from './provider-flash'
import { modalProvider } from './provider-modal'

export const enum Status {
  PENDING = 'PENDING',
  PROCESSING = 'PROCESSING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED'
}

export interface BeamConfig {
  url: string
  taskApi: string
}

export interface FlashConfig {
  url: string
  endpointName: string
}

export interface ModalConfig {
  url: string
}

export interface ProviderConfigs {
  beam: BeamConfig
  flash: FlashConfig
  modal: ModalConfig
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
  flash: flashProvider,
  modal: modalProvider
}

export function isProviderName(value: string): value is ProviderName {
  return value === 'beam' || value === 'flash' || value === 'modal'
}

export default function createProvider<K extends ProviderName>(name: K): Provider<K> {
  return providers[name]
}
