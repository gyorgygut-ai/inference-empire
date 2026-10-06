import { Status, type Provider } from './create-provider'

export const modalProvider: Provider<'modal'> = {
  encodeTaskId(originalTaskId: string): string {
    return btoa(`modal:${originalTaskId}`)
  },
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string } {
    const [provider, originalTaskId] = atob(encoded).split(':')
    return { provider, originalTaskId }
  },
  async pushToTaskQueue(input, config) {
    const response = await fetch(`${config.url}/infer`, {
      method: 'POST',
      headers: modalHeaders(config),
      body: JSON.stringify({ input })
    })
    const result: { task_id: string } = await response.json()
    return { task_id: result.task_id }
  },
  async fetchTaskStatus(taskId, config) {
    const response = await fetch(`${config.url}/inquire?id=${encodeURIComponent(taskId)}`, {
      headers: modalHeaders(config)
    })
    const result: { status: string; output?: unknown } = await response.json()
    return {
      status: mapTaskStatusToResponse(result.status),
      output: result.output
    }
  }
}

function modalHeaders(config: { proxyKey: string; proxySecret: string }): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    'Modal-Key': config.proxyKey,
    'Modal-Secret': config.proxySecret
  }
}

function mapTaskStatusToResponse(providerStatus: string): Status {
  const mapping: Record<string, Status> = {
    'completed': Status.COMPLETED,
    'failed': Status.FAILED,
    'cancelled': Status.CANCELLED,
    'processing': Status.PROCESSING,
    'pending': Status.PENDING,
    'rejected': Status.REJECTED
  }
  return mapping[providerStatus] || Status.PENDING
}
