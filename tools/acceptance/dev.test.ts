import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parse } from 'dotenv';
import { expect, test } from 'vitest';
import { createRequire } from 'node:module';
import { TaskQueueServiceContractFlux2Dev, taskQueueServiceFlux2DevSchema } from '../../packages/contracts/task-queue-service/flux2-dev.contract.ts';

const require = createRequire(import.meta.url);
const { getReadyUrl } = require('/Users/gyorgygutai/Projects/personal/inference-empire/node_modules/nx/dist/src/tasks-runner/readiness/ready-signal');

const readEnv = (path: string) => parse(readFileSync(fileURLToPath(new URL(path, import.meta.url))));

const devEnv = readEnv(`../../${TaskQueueServiceContractFlux2Dev.envFilePath}`);
const routerUrl = devEnv.ROUTER_RESOLVED_URL;
const faceValueUrl = getReadyUrl('http://127.0.0.1:3000');

test('flux2-dev TaskQueueServiceContract fulfilled', () => {
  expect(taskQueueServiceFlux2DevSchema.parse(devEnv)).toEqual(devEnv);
});

test('ROUTER_RESOLVED_URL eq http://127.0.0.1:5050', () => {
  expect(routerUrl).toBe('http://127.0.0.1:5050');
});

test('router responds', async () => {
  const response = await fetch(`${routerUrl}/sup`);
  expect(response.ok).toBe(true);
});

test('face-value responds', async () => {
  const response = await fetch(faceValueUrl);
  expect(response.ok).toBe(true);
});
