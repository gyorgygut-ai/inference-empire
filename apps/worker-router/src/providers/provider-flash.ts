import { Status } from './create-provider'

export const flashProvider = {
  encodeTaskId(originalTaskId: string): string {
    return btoa(`flash:${originalTaskId}`)
  },
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string } {
    const [provider, originalTaskId] = atob(encoded).split(':')
    return { provider, originalTaskId }
  },
  async pushToTaskQueue(prompt: string): Promise<{ task_id: string }> {
    const response = await fetch(`${process.env.FLASH_API_URL}/endpoints/flux2`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${process.env.FLASH_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    })
    const result = await response.json()
    const taskId = `flash-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    return { task_id: taskId }
  },
  async fetchTaskStatus(taskId: string): Promise<{ status: Status; output?: unknown }> {
    const response = await fetch(`${process.env.FLASH_API_URL}/endpoints/flux2`, {
      headers: { 'Authorization': `Bearer ${process.env.FLASH_TOKEN}` }
    })
    const result = await response.json()
    return {
      status: flashProvider.mapTaskStatusToResponse('success'),
      output: result
    }
  },
  mapTaskStatusToResponse(providerStatus: string): Status {
    const mapping: Record<string, Status> = {
      'success': Status.COMPLETED,
      'error': Status.FAILED
    }
    return mapping[providerStatus] || Status.PENDING
  }
}
