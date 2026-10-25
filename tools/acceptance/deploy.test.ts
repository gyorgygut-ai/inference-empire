import { readFileSync } from "node:fs";
import { test, expect } from "vitest";
import { WorkerServiceContractFlux2Deploy, workerServiceFlux2DeploySchema, TaskQueueServiceContractFlux2Deploy, taskQueueServiceFlux2DeploySchema } from "file:///Users/gyorgygutai/Projects/personal/inference-empire/packages/contracts/src/index.ts";

const readEnv = (contract) => Object.fromEntries(readFileSync(contract.envFilePath, "utf-8").split("\n").filter(Boolean).map(l => l.split("=")));

const workerEnv = readEnv(WorkerServiceContractFlux2Deploy);
const queueEnv = readEnv(TaskQueueServiceContractFlux2Deploy);

test("flux2-deploy WorkerServiceContract fulfilled", () => {
  const parsed = workerServiceFlux2DeploySchema.parse(workerEnv);
  expect(parsed).toEqual(workerEnv);
});

test("flux2-deploy TaskQueueServiceContract fulfilled", () => {
  const parsed = taskQueueServiceFlux2DeploySchema.parse(queueEnv);
  expect(parsed).toEqual(queueEnv);
});
