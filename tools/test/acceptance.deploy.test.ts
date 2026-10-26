import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { parse } from 'dotenv'
import { expect, test } from 'vitest'
import {
  TaskQueueServiceFlux2DeployContract,
  taskQueueServiceFlux2DeploySchema,
} from '@inference/contracts/task-queue-service/flux2-deploy.contract.ts'
import {
  WorkerServiceFlux2DeployContract,
  workerServiceFlux2DeploySchema,
} from '@inference/contracts/worker-service/flux2-deploy.contract.ts'

const readContractEnv = (path: string) =>
  parse(readFileSync(resolve(process.cwd(), '../..', path), 'utf8'))

const workerEnv = workerServiceFlux2DeploySchema.parse(
  readContractEnv(WorkerServiceFlux2DeployContract.envFilePath),
)
const queueEnv = taskQueueServiceFlux2DeploySchema.parse(
  readContractEnv(TaskQueueServiceFlux2DeployContract.envFilePath),
)

test('Flux2 deploy worker contract resolves', () => {
  expect(workerEnv.WORKER_RESOLVED_BEAM_URL).toBeTruthy()
})

test('Flux2 deploy task-queue contract resolves', () => {
  expect(queueEnv.ROUTER_RESOLVED_URL).toBeTruthy()
})

test('Flux2 worker responds', async () => {
  const response = await fetch(workerEnv.WORKER_RESOLVED_BEAM_URL, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.BEAM_TOKEN ?? ''}` }, body: JSON.stringify({ prompt: 'ping' }) })
  expect(response.status).not.toBe(404)
  expect(response.status).toBeLessThan(500)
})

test('Flux2 router responds', async () => {
  const response = await fetch(`${queueEnv.ROUTER_RESOLVED_URL}/flux2/sup`, {
    headers: { Authorization: `Bearer ${queueEnv.ROUTER_GENERATED_AUTH_TOKEN}` },
  })
  expect(response.status).toBe(400)
})
