import { Status, type Env } from './create-provider'

export const flashProvider = {
  encodeTaskId(originalTaskId: string): string {
    return btoa(`flash:${originalTaskId}`)
  },
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string } {
    const [provider, originalTaskId] = atob(encoded).split(':')
    return { provider, originalTaskId }
  },
  async pushToTaskQueue(input: Record<string, unknown>, env: Env): Promise<{ task_id: string }> {
    const response = await fetch(`${env.PROVIDER_API_URL}/endpoints/${env.PROVIDER_ENDPOINT_NAME}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${env.PROVIDER_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ input })
    })
    const result = await response.json()
    const taskId = `flash-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    return { task_id: taskId }
  },
  async fetchTaskStatus(taskId: string, env: Env): Promise<{ status: Status; output?: unknown }> {
    const response = await fetch(`${env.PROVIDER_API_URL}/endpoints/${env.PROVIDER_ENDPOINT_NAME}`, {
      headers: { 'Authorization': `Bearer ${env.PROVIDER_TOKEN}` }
    })
    const result = await response.json()
    return {
      status: mapTaskStatusToResponse('success'),
      output: result
    }
  }
}

function mapTaskStatusToResponse(providerStatus: string): Status {
  const mapping: Record<string, Status> = {
    'success': Status.COMPLETED,
    'error': Status.FAILED
  }
  return mapping[providerStatus] || Status.PENDING
}
