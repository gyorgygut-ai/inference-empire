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
    const response = await fetch(config.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
    const result = await response.json() as Record<string, unknown>
    return { task_id: result.task_id ?? `modal-${Date.now()}-${Math.random().toString(36).slice(2, 9)}` }
  },
  async fetchTaskStatus(_taskId, config) {
    // Modal worker is synchronous per request; no status polling
    return { status: Status.COMPLETED, output: undefined }
  }
}
