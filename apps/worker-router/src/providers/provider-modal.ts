import { Status } from './create-provider'

export const modalProvider = {
  encodeTaskId(originalTaskId: string): string {
    return btoa(`modal:${originalTaskId}`)
  },
  decodeTaskId(encoded: string): { provider: string; originalTaskId: string } {
    const [provider, originalTaskId] = atob(encoded).split(':')
    return { provider, originalTaskId }
  },
  async pushToTaskQueue(prompt: string): Promise<{ task_id: string }> {
    const response = await fetch(`${process.env.MODAL_API_URL}/functions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${process.env.MODAL_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ function: 'flux2', args: [prompt] })
    })
    const { call_id } = await response.json()
    return { task_id: call_id }
  },
  async fetchTaskStatus(taskId: string): Promise<{ status: Status; output?: unknown }> {
    const response = await fetch(`${process.env.MODAL_API_URL}/functions/${taskId}`, {
      headers: { 'Authorization': `Bearer ${process.env.MODAL_TOKEN}` }
    })
    const result = await response.json()
    return {
      status: modalProvider.mapTaskStatusToResponse(result.state),
      output: result
    }
  },
  mapTaskStatusToResponse(providerStatus: string): Status {
    const mapping: Record<string, Status> = {
      'succeeded': Status.COMPLETED,
      'failed': Status.FAILED,
      'running': Status.PROCESSING,
      'queued': Status.PENDING
    }
    return mapping[providerStatus] || Status.PENDING
  }
}
