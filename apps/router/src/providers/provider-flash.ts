import { Status, type Provider } from './create-provider.js'

export const flashProvider: Provider<'flash'> = {
  encodeTaskId(originalTaskId: string): string {
    return btoa(`flash:${originalTaskId}`)
  },
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string } {
    const [provider, originalTaskId] = atob(encoded).split(':')
    return { provider, originalTaskId }
  },
  async pushToTaskQueue(input, config) {
    await fetch(`${config.url}/endpoints/${config.endpointName}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input })
    })
    const taskId = `flash-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    return { task_id: taskId }
  },
  async fetchTaskStatus(_taskId, config) {
    const response = await fetch(`${config.url}/endpoints/${config.endpointName}`)
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
