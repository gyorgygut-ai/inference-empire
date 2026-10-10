import { Status, type Provider } from './create-provider'

export const beamProvider: Provider<'beam'> = {
  encodeTaskId(originalTaskId: string): string {
    return btoa(`beam:${originalTaskId}`)
  },
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string } {
    const [provider, originalTaskId] = atob(encoded).split(':')
    return { provider, originalTaskId }
  },
  async pushToTaskQueue(input, config) {
    const response = await fetch(`${config.url}/queues/default`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input })
    })
    const result: { task_id: string } = await response.json()
    return { task_id: result.task_id }
  },
  async fetchTaskStatus(taskId, config) {
    const response = await fetch(`${config.url}/queues/default/${taskId}`)
    const result: { status: string; output?: unknown } = await response.json()
    return {
      status: mapTaskStatusToResponse(result.status),
      output: result.output
    }
  }
}

function mapTaskStatusToResponse(providerStatus: string): Status {
  const mapping: Record<string, Status> = {
    'COMPLETED': Status.COMPLETED,
    'FAILED': Status.FAILED,
    'RUNNING': Status.PROCESSING,
    'PENDING': Status.PENDING
  }
  return mapping[providerStatus] || Status.PENDING
}
