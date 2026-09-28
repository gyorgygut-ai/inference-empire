import { Status } from './create-provider'

export const beamProvider = {
  encodeTaskId(originalTaskId: string): string {
    return btoa(`beam:${originalTaskId}`)
  },
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string } {
    const [provider, originalTaskId] = atob(encoded).split(':')
    return { provider, originalTaskId }
  },
  async pushToTaskQueue(prompt: string): Promise<{ task_id: string }> {
    const response = await fetch(`${process.env.BEAM_API_URL}/queues/default`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${process.env.BEAM_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, model: 'flux2' })
    })
    const { task_id } = await response.json()
    return { task_id }
  },
  async fetchTaskStatus(taskId: string): Promise<{ status: Status; output?: unknown }> {
    const response = await fetch(`${process.env.BEAM_API_URL}/queues/default/${taskId}`, {
      headers: { 'Authorization': `Bearer ${process.env.BEAM_TOKEN}` }
    })
    const result = await response.json()
    return {
      status: beamProvider.mapTaskStatusToResponse(result.status),
      output: result
    }
  },
  mapTaskStatusToResponse(providerStatus: string): Status {
    const mapping: Record<string, Status> = {
      'COMPLETED': Status.COMPLETED,
      'FAILED': Status.FAILED,
      'RUNNING': Status.PROCESSING,
      'PENDING': Status.PENDING
    }
    return mapping[providerStatus] || Status.PENDING
  }
}
