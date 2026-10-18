export type Status = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

export interface TaskQueueApi<I, O> {
  AddToQueueRequest: { input: I }
  AddToQueueResponse: { task_id: string }
  SupResponse: { status: Status; output?: O }
}
