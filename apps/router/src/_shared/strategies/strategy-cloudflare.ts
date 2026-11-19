import { z } from 'zod'
import type { RuntimeConfig } from '../config'
import { StrategyUnavailableError, taskStatusSchema, type Strategy } from './strategy'

const taskResponse = z.object({ task_id: z.string().min(1) })
const statusResponse = z.object({
  status: taskStatusSchema,
  output: z.unknown().optional(),
})

export function strategyCloudflare(config: RuntimeConfig, fetchImpl: typeof fetch = fetch): Strategy {
  const headers = { Authorization: `Bearer ${config.routerToken}` }
  function cloudflareUrl() {
    if (!config.cloudflareUrl) {throw new StrategyUnavailableError('Cloudflare is not configured')}
    return config.cloudflareUrl
  }
  async function fetchWorker(path: string, init: RequestInit) {
    const request = new Request(new URL(path, cloudflareUrl()), init)
    if (config.cloudflareWorker) {
      return config.cloudflareWorker.fetch(request)
    }
    return fetchImpl(request)
  }

  return {
    async pushToTaskQueue(input) {
      const response = await fetchWorker('/generate', {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      })
      if (!response.ok) {throw new Error(`Cloudflare generate returned ${response.status}`)}
      return taskResponse.parse(await response.json())
    },

    async fetchTaskStatus(taskId) {
      const response = await fetchWorker(`/tasks/${encodeURIComponent(taskId)}`, {
        headers,
      })
      if (!response.ok) {throw new Error(`Cloudflare task returned ${response.status}`)}
      const result = statusResponse.parse(await response.json())
      return { status: result.status, output: result.output }
    },
  }
}
