import { z } from 'zod'

export type Provider = 'beam' | 'cloudflare'
export const providerSchema = z.enum(['beam', 'cloudflare'])
export const taskStatusSchema = z.enum(['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'])
export type TaskStatus = z.infer<typeof taskStatusSchema>
export interface Strategy {
  pushToTaskQueue(input: unknown): Promise<{ task_id: string }>;
  fetchTaskStatus(taskId: string): Promise<{ status: TaskStatus; output?: unknown }>;
}

export class StrategyUnavailableError extends Error {}
