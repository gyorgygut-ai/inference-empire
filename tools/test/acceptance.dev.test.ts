import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { parse } from 'dotenv'
import { expect, test } from 'vitest'
import { TaskQueueServiceFlux2DevContract, taskQueueServiceFlux2DevSchema } from '@inference/contracts/task-queue-service/flux2-dev.contract.ts'
import { WorkerServiceFlux2DeployContract, workerServiceFlux2DeploySchema } from '@inference/contracts/worker-service/flux2-deploy.contract.ts'

const readEnv = (path: string) => parse(readFileSync(resolve(process.cwd(), '../..', path), 'utf8'))

const devEnv = readEnv(TaskQueueServiceFlux2DevContract.envFilePath)
const workerEnv = workerServiceFlux2DeploySchema.parse(readEnv(WorkerServiceFlux2DeployContract.envFilePath))

test('Flux2 dev task-queue contract resolves', () => expect(taskQueueServiceFlux2DevSchema.parse(devEnv)).toEqual(devEnv))
test('Flux2 deploy worker contract resolves', () => expect(workerEnv.WORKER_RESOLVED_BEAM_URL).toBeTruthy())
test('Flux2 worker responds', async () => {
  const response = await fetch(workerEnv.WORKER_RESOLVED_BEAM_URL, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.BEAM_TOKEN ?? ''}` }, body: JSON.stringify({ prompt: 'ping' }) })
  expect(response.status).not.toBe(404)
  expect(response.status).toBeLessThan(500)
})
test('Flux2 router responds', async () => expect((await fetch('http://127.0.0.1:4000/flux2/sup', { headers: { Authorization: `Bearer ${devEnv.ROUTER_GENERATED_AUTH_TOKEN}` } })).status).toBe(400))
test('Face Value responds', async () => expect((await fetch('http://127.0.0.1:3000')).ok).toBe(true))
