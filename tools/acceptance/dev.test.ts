import { readFileSync } from "node:fs";
import { test, expect } from "vitest";
import { WorkerServiceContractFlux2Dev, workerServiceFlux2DevSchema, TaskQueueServiceContractFlux2Dev, taskQueueServiceFlux2DevSchema } from "file:///Users/gyorgygutai/Projects/personal/inference-empire/packages/contracts/src/index.ts";

const readEnv = (contract) => Object.fromEntries(readFileSync(contract.envFilePath, "utf-8").split("\n").filter(Boolean).map(l => l.split("=")));

const workerEnv = readEnv(WorkerServiceContractFlux2Dev);
const queueEnv = readEnv(TaskQueueServiceContractFlux2Dev);

test("flux2-dev WorkerServiceContract fulfilled", () => {
  const parsed = workerServiceFlux2DevSchema.parse(workerEnv);
  expect(parsed).toEqual(workerEnv);
});

test("flux2-dev TaskQueueServiceContract fulfilled", () => {
  const parsed = taskQueueServiceFlux2DevSchema.parse(queueEnv);
  expect(parsed).toEqual(queueEnv);
});

test("ROUTER_RESOLVED_URL eq http://127.0.0.1:5050", () => {
  expect(queueEnv.ROUTER_RESOLVED_URL).toBe("http://127.0.0.1:5050");
});
