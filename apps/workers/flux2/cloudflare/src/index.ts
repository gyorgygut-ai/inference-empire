import { z } from 'zod'
import { Router } from 'itty-router'
import { api } from '../dist/flux2.schema'
import type { RuntimeEnv } from './env'
import { processGeneration, taskRecordSchema, toWorkersAiForm, validateWorkersAiInput, type Flux2Input, type TaskRecord } from './processor'
import { TaskState } from './task-state'

const taskIdSchema = z.string().uuid()
const artifactLifetimeSeconds = 60 * 60
const deliveriesBeforeFailure = 4

function json(body: unknown, statusCode = 200): Response {
  return Response.json(body, { status: statusCode })
}

function logError(entry: Record<string, string | number>): void {
  // oxlint-disable-next-line no-console
  console.error(JSON.stringify(entry))
}

async function tokenMatches(provided: string | null, expected: string | undefined): Promise<boolean> {
  if (!provided || !expected) {return false}
  const encoder = new TextEncoder()
  const [providedDigest, expectedDigest] = await Promise.all([
    crypto.subtle.digest('SHA-256', encoder.encode(provided)),
    crypto.subtle.digest('SHA-256', encoder.encode(expected)),
  ])
  const left = new Uint8Array(providedDigest)
  const right = new Uint8Array(expectedDigest)
  let difference = 0
  for (let index = 0; index < left.length; index += 1) {difference |= left[index] ^ right[index]}
  return difference === 0
}

async function authorized(request: Request, env: RuntimeEnv): Promise<boolean> {
  const value = request.headers.get('Authorization')
  return tokenMatches(value?.startsWith('Bearer ') ? value.slice(7) : null, env.AUTH_TOKEN)
}

function taskStub(env: RuntimeEnv, taskId: string): DurableObjectStub {
  const id = env.TASKS.idFromName(taskId)
  return env.TASKS.get(id)
}

async function readTask(env: RuntimeEnv, taskId: string): Promise<TaskRecord | null> {
  const response = await taskStub(env, taskId).fetch('https://task-state/')
  if (response.status === 404) {return null}
  if (!response.ok) {throw new Error(`Task state lookup returned ${response.status}`)}
  return taskRecordSchema.parse(await response.json())
}

async function writeTask(env: RuntimeEnv, taskId: string, record: TaskRecord): Promise<void> {
  const response = await taskStub(env, taskId).fetch('https://task-state/', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  })
  if (!response.ok) {throw new Error(`Task state update returned ${response.status}`)}
}

async function signArtifactUrl(origin: string, taskId: string, token: string): Promise<string> {
  const expires = Math.floor(Date.now() / 1000) + artifactLifetimeSeconds
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(token), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  )
  const signatureBytes = new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`${taskId}\n${expires}`)))
  const signature = btoa(String.fromCharCode(...signatureBytes)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '')
  const url = new URL(`/artifacts/${taskId}`, origin)
  url.searchParams.set('expires', String(expires))
  url.searchParams.set('signature', signature)
  return url.toString()
}

async function verifyArtifactSignature(taskId: string, expires: string | null, signature: string | null, token: string): Promise<boolean> {
  if (!expires || !signature || !/^\d+$/.test(expires) || Number(expires) < Math.floor(Date.now() / 1000)) {return false}
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(token), { name: 'HMAC', hash: 'SHA-256' }, false, ['verify'],
  )
  const bytes = Uint8Array.from(atob(signature.replaceAll('-', '+').replaceAll('_', '/')), (character) => character.charCodeAt(0))
  return crypto.subtle.verify('HMAC', key, bytes, new TextEncoder().encode(`${taskId}\n${expires}`))
}

async function generate(request: Request, env: RuntimeEnv): Promise<Response> {
  if (!(await authorized(request, env))) {return json({ error: env.AUTH_TOKEN ? 'Unauthorized' : 'Worker not configured' }, env.AUTH_TOKEN ? 401 : 503)}
  let body: unknown
  try { body = await request.json() }
  catch { return json({ error: 'Invalid JSON' }, 400) }
  const input = api.shape.input.safeParse(body)
  if (!input.success) {return json({ error: 'Invalid input' }, 400)}
  try { validateWorkersAiInput(input.data) }
  catch { return json({ error: 'Invalid input for Cloudflare FLUX.2' }, 400) }

  const taskId = crypto.randomUUID()
  try {
    await writeTask(env, taskId, { status: 'PENDING' })
    await env.FLUX2_QUEUE.send({ taskId, input: input.data })
    return json({ task_id: taskId }, 202)
  } catch (error) {
    logError({ message: 'failed to enqueue FLUX.2 task', taskId, error: String(error) })
    try { await writeTask(env, taskId, { status: 'FAILED', error: 'Could not enqueue task' }) }
    catch (stateError) { logError({ message: 'failed to persist enqueue failure', taskId, error: String(stateError) }) }
    return json({ error: 'Could not enqueue task' }, 503)
  }
}

async function taskResult(request: Request, env: RuntimeEnv, taskId: string): Promise<Response> {
  if (!(await authorized(request, env))) {return json({ error: env.AUTH_TOKEN ? 'Unauthorized' : 'Worker not configured' }, env.AUTH_TOKEN ? 401 : 503)}
  if (!taskIdSchema.safeParse(taskId).success) {return json({ error: 'Invalid task id' }, 400)}
  const record = await readTask(env, taskId)
  if (!record) {return json({ error: 'Task not found' }, 404)}
  if (record.status !== 'COMPLETED') {
    return json({ status: record.status === 'FAILED' ? 'FAILED' : record.status })
  }
  if (!env.AUTH_TOKEN) {return json({ error: 'Worker not configured' }, 503)}
  const presignedUrl = await signArtifactUrl(new URL(request.url).origin, taskId, env.AUTH_TOKEN)
  return json({ status: 'COMPLETED', output: { artifact: { presigned_url: presignedUrl } } })
}

async function artifact(request: Request, env: RuntimeEnv, taskId: string): Promise<Response> {
  if (!taskIdSchema.safeParse(taskId).success || !env.AUTH_TOKEN) {return new Response('Not found', { status: 404 })}
  const url = new URL(request.url)
  try {
    if (!(await verifyArtifactSignature(taskId, url.searchParams.get('expires'), url.searchParams.get('signature'), env.AUTH_TOKEN))) {
      return new Response('Not found', { status: 404 })
    }
  } catch { return new Response('Not found', { status: 404 }) }
  const record = await readTask(env, taskId)
  if (record?.status !== 'COMPLETED') {return new Response('Not found', { status: 404 })}
  const object = await env.ARTIFACTS.get(record.artifactKey)
  if (!object) {return new Response('Not found', { status: 404 })}
  const headers = new Headers({ 'Content-Type': record.contentType, 'Cache-Control': 'private, max-age=3600' })
  object.writeHttpMetadata(headers)
  return new Response(object.body, { headers })
}

const router = Router()

router.get('/health', () => json({ status: 'ok' }))
router.post('/generate', (request: Request, env: RuntimeEnv) => generate(request, env))
router.get('/tasks/:taskId', (request: Request & { params: Record<string, string> }, env: RuntimeEnv) =>
  taskResult(request, env, request.params.taskId))
router.get('/artifacts/:taskId', (request: Request & { params: Record<string, string> }, env: RuntimeEnv) =>
  artifact(request, env, request.params.taskId))
router.all('*', () => json({ error: 'Not Found' }, 404))

export default {
  fetch: (request: Request, env: RuntimeEnv, ctx: ExecutionContext): Promise<Response> =>
    router.fetch(request, env, ctx),

  async queue(batch: MessageBatch<{ taskId: string; input: Flux2Input }>, env: RuntimeEnv): Promise<void> {
    for (const message of batch.messages) {
      const job = message.body
      if (!taskIdSchema.safeParse(job.taskId).success) {
        message.ack()
        continue
      }
      try {
        await processGeneration(job.taskId, job.input, {
          getTask: (taskId) => readTask(env, taskId),
          setTask: (taskId, record) => writeTask(env, taskId, record),
          async runModel(input) {
            const multipart = toWorkersAiForm(input)
            const result = z.object({ image: z.string().min(1) }).parse(await env.AI.run(
              '@cf/black-forest-labs/flux-2-klein-9b',
              { multipart: { body: multipart.body, contentType: multipart.contentType } },
            ))
            return result.image
          },
          async putArtifact(key, bytes, contentType) {
            await env.ARTIFACTS.put(key, bytes, { httpMetadata: { contentType } })
          },
        })
        message.ack()
      } catch (error) {
        logError({ message: 'FLUX.2 queue delivery failed', taskId: job.taskId, attempts: message.attempts, error: String(error) })
        if (message.attempts >= deliveriesBeforeFailure) {
          try { await writeTask(env, job.taskId, { status: 'FAILED', error: 'FLUX.2 generation failed' }) }
          catch (stateError) { logError({ message: 'failed to persist generation failure', taskId: job.taskId, error: String(stateError) }) }
          message.ack()
        } else {
          message.retry({ delaySeconds: 5 })
        }
      }
    }
  },
} satisfies ExportedHandler<RuntimeEnv, { taskId: string; input: Flux2Input }>

export { TaskState }
