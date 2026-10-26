import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { parse } from 'dotenv'
import { expect, test } from 'vitest'
import {
  TaskQueueServiceKrea2DevContract,
  taskQueueServiceKrea2DevSchema,
} from '@inference/contracts/task-queue-service/krea2-dev.contract.ts'
import {
  WorkerServiceKrea2DeployContract,
  workerServiceKrea2DeploySchema,
} from '@inference/contracts/worker-service/krea2-deploy.contract.ts'

const env = parse(
  readFileSync(resolve(process.cwd(), '../..', TaskQueueServiceKrea2DevContract.envFilePath), 'utf8'),
)
const workerEnv = workerServiceKrea2DeploySchema.parse(
  parse(readFileSync(resolve(process.cwd(), '../..', WorkerServiceKrea2DeployContract.envFilePath), 'utf8')),
)

test('Krea2 dev task-queue contract resolves', () => expect(taskQueueServiceKrea2DevSchema.parse(env)).toEqual(env))
test('Krea2 deploy worker contract resolves', () => expect(workerEnv.WORKER_RESOLVED_BEAM_URL).toBeTruthy())
test('Krea2 worker responds', async () => {
  const response = await fetch(workerEnv.WORKER_RESOLVED_BEAM_URL, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.BEAM_TOKEN ?? ''}` }, body: JSON.stringify({ prompt: 'ping' }) })
  expect(response.status).not.toBe(404)
  expect(response.status).toBeLessThan(500)
})
test('Krea2 router responds', async () => expect((await fetch('http://127.0.0.1:4025/krea2/sup', { headers: { Authorization: `Bearer ${env.ROUTER_GENERATED_AUTH_TOKEN}` } })).status).toBe(400))
