import { z } from 'zod'
import type { RuntimeConfig } from '../config'
import { taskStatusSchema, type Strategy } from './strategy'

const queueResponse = z.object({ task_id: z.string().min(1) })
const beamStatus = z.enum(['PENDING', 'RETRY', 'RUNNING', 'COMPLETE', 'ERROR', 'CANCELLED', 'TIMEOUT'])
const workspaceResponse = z.object({ external_id: z.string().min(1) })
const statusResponse = z.object({ status: beamStatus, result: z.unknown().nullable().optional() })
const statuses = {
  PENDING: 'PENDING', RETRY: 'PENDING', RUNNING: 'PROCESSING', COMPLETE: 'COMPLETED',
  ERROR: 'FAILED', CANCELLED: 'CANCELLED', TIMEOUT: 'FAILED',
}

export function strategyBeam(config: RuntimeConfig, fetchImpl: typeof fetch = fetch): Strategy {
  const headers = { Authorization: `Bearer ${config.beamToken}` }
  return {
    async pushToTaskQueue(input) {
      const response = await fetchImpl(config.beamUrl, {
        method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify(input),
      })
      if (!response.ok) {throw new Error(`Beam queue returned ${response.status}`)}
      return queueResponse.parse(await response.json())
    },
    async fetchTaskStatus(taskId) {
      const workspaceResponseResult = await fetchImpl('https://app.beam.cloud/api/v1/workspace/current', { headers })
      if (!workspaceResponseResult.ok) {throw new Error(`Beam workspace returned ${workspaceResponseResult.status}`)}
      const workspaceId = workspaceResponse.parse(await workspaceResponseResult.json()).external_id
      const response = await fetchImpl(`https://app.beam.cloud/api/v1/task/${encodeURIComponent(workspaceId)}/${encodeURIComponent(taskId)}`, { headers })
      if (!response.ok) {throw new Error(`Beam task returned ${response.status}`)}
      const result = statusResponse.parse(await response.json())
      return { status: taskStatusSchema.parse(statuses[result.status]), output: result.result ?? undefined }
    },
  }
}
