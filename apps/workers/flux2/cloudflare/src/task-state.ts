import { DurableObject } from 'cloudflare:workers'
import { taskRecordSchema, type TaskRecord } from './processor'

export class TaskState extends DurableObject<Env> {
  async fetch(request: Request): Promise<Response> {
    if (request.method === 'GET') {
      const record = await this.ctx.storage.get<TaskRecord>('record')
      return record ? Response.json(record) : Response.json({ error: 'Task not found' }, { status: 404 })
    }
    if (request.method === 'PUT') {
      let body: unknown
      try { body = await request.json() }
      catch { return Response.json({ error: 'Invalid JSON' }, { status: 400 }) }
      const record = taskRecordSchema.safeParse(body)
      if (!record.success) {return Response.json({ error: 'Invalid task state' }, { status: 400 })}
      await this.ctx.storage.put('record', record.data)
      return new Response(null, { status: 204 })
    }
    return new Response(null, { status: 405, headers: { Allow: 'GET, PUT' } })
  }
}
