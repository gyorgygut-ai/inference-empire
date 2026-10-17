import type { Env } from '../../env.schema.js'
import { beamProvider } from './provider-beam.js'
import { flashProvider } from './provider-flash.js'
import { modalProvider } from './provider-modal.js'

export const enum Status {
  PENDING = 'PENDING',
  PROCESSING = 'PROCESSING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED'
}

export interface BeamConfig {
  url: string
}

export interface FlashConfig {
  url: string
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
  resolveConfig(env: Env): ProviderConfigs[K] | undefined
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
  return Object.hasOwn(providers, value)
}

export function decodeProviderName(encoded: string): string {
  return atob(encoded).split(':', 1)[0]
}

export default function createProvider<K extends ProviderName>(name: K): Provider<K> {
  return providers[name]
}
