import { Status, type Env } from './create-provider'

export const modalProvider = {
  encodeTaskId(originalTaskId: string): string {
    return btoa(`modal:${originalTaskId}`)
  },
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string } {
    const [provider, originalTaskId] = atob(encoded).split(':')
    return { provider, originalTaskId }
  },
  async pushToTaskQueue(input: Record<string, unknown>, env: Env): Promise<{ task_id: string }> {
    const appName = env.PROVIDER_APP_NAME
    if (!appName) {
      throw new Error('PROVIDER_APP_NAME is required for modal provider')
    }
    const response = await fetch(`${env.PROVIDER_API_URL}/functions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${env.PROVIDER_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ function: appName, args: [input] })
    })
    const result: { call_id: string } = await response.json()
    return { task_id: result.call_id }
  },
  async fetchTaskStatus(taskId: string, env: Env): Promise<{ status: Status; output?: unknown }> {
    const response = await fetch(`${env.PROVIDER_API_URL}/functions/${taskId}`, {
      headers: { 'Authorization': `Bearer ${env.PROVIDER_TOKEN}` }
    })
    const result: { state: string; output?: unknown } = await response.json()
    return {
      status: mapTaskStatusToResponse(result.state),
      output: result.output
    }
  }
}

function mapTaskStatusToResponse(providerStatus: string): Status {
  const mapping: Record<string, Status> = {
    'succeeded': Status.COMPLETED,
    'failed': Status.FAILED,
    'running': Status.PROCESSING,
    'queued': Status.PENDING
  }
  return mapping[providerStatus] || Status.PENDING
}
