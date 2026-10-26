import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { parse } from 'dotenv';
import type { PromiseExecutor } from '@nx/devkit';
import { runCommands } from 'nx/src/executors/run-commands/run-commands.impl';
import { updateEnvFile } from '../../../../update-env-file.ts';
import type { ContractModule, RunCommandExecutorSchema } from './schema';

const CONTRACTS_DIR = 'packages/contracts';

async function loadContracts(root: string): Promise<Map<string, ContractModule>> {
  const contracts = new Map<string, ContractModule>();
  const requireContract = createRequire(resolve(root, 'package.json'));
  const servicesDir = resolve(root, CONTRACTS_DIR);
  for (const service of readdirSync(servicesDir, { withFileTypes: true })) {
    if (!service.isDirectory()) {
      continue;
    }
    const serviceDir = resolve(servicesDir, service.name);
    for (const file of readdirSync(serviceDir).filter((entry) => entry.endsWith('.contract.ts'))) {
      const module = requireContract(resolve(serviceDir, file)) as Record<string, unknown>;
      for (const value of Object.values(module)) {
        if (
          typeof value === 'object' &&
          value !== null &&
          Array.isArray((value as ContractModule).keys) &&
          typeof (value as ContractModule).envFilePath === 'string'
        ) {
          const contract = value as ContractModule;
          contracts.set(`${service.name}/${file.replace('.contract.ts', '')}`, contract);
        }
      }
    }
  }
  return contracts;
}

function envPath(root: string, contract: ContractModule): string {
  return resolve(root, contract.envFilePath);
}

function fulfilledValue(recorded: string): string | undefined {
  return recorded
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .at(-1);
}

const runExecutor: PromiseExecutor<RunCommandExecutorSchema> = async (options, context) => {
  const own = (context.target?.options ?? {}) as Partial<RunCommandExecutorSchema>;
  const command = own.command ?? options.command;
  const args = own.args ?? options.args ?? '';
  const env = options.env ?? {};
  const cwd = own.cwd ?? options.cwd;
  const needs = own.needs ?? options.needs ?? [];
  const fulfills = own.fulfills ?? options.fulfills ?? [];
  const envKey = own.envKey ?? options.envKey;
  const envFile = own.envFile ?? options.envFile;

  const contracts = await loadContracts(context.root);

  const lookup = (name: string): ContractModule => {
    const contract = contracts.get(name);
    if (!contract) {
      throw new Error(
        `Unknown contract "${name}". Available: ${[...contracts.keys()].sort().join(', ')}`,
      );
    }
    return contract;
  };

  const inherited: NodeJS.ProcessEnv = { ...process.env };
  for (const need of needs) {
    const contract = lookup(need.contract);
    const file = envPath(context.root, contract);
    if (!existsSync(file)) {
      throw new Error(`Contract "${need.contract}" is not fulfilled: ${file} does not exist`);
    }
    Object.assign(inherited, parse(readFileSync(file)));
  }
  if (envFile) {
    const file = resolve(context.root, envFile);
    if (existsSync(file)) {
      Object.assign(inherited, parse(readFileSync(file)));
    }
  }
  Object.assign(inherited, env);

  for (const need of needs) {
    if (need.contractKey && inherited[need.contractKey] === undefined) {
      throw new Error(`Contract "${need.contract}" is missing "${need.contractKey}"`);
    }
  }

  for (const fulfillment of fulfills) {
    const contract = lookup(fulfillment.contract);
    if (!contract.keys.includes(fulfillment.contractKey)) {
      throw new Error(
        `Contract "${fulfillment.contract}" does not own "${fulfillment.contractKey}". Keys: ${contract.keys.join(', ')}`,
      );
    }
  }

  const runningTask = await runCommands(
    {
      command: [command, args].filter(Boolean).join(' '),
      cwd: cwd ? resolve(context.root, cwd) : context.root,
      env: Object.fromEntries(
        Object.entries(inherited).filter(
          (entry): entry is [string, string] => entry[1] !== undefined,
        ),
      ),
      streamOutput: true,
      __unparsed__: [],
    },
    context,
  );
  const { code, terminalOutput } = await runningTask.getResults();

  if (code !== 0) {
    return { success: false };
  }

  if (fulfills.length === 0 && !(envFile && envKey)) {
    return { success: true };
  }

  const value = fulfilledValue(terminalOutput);

  for (const fulfillment of fulfills) {
    if (!value) {
      return { success: false, error: `No output to fulfill "${fulfillment.contractKey}"` };
    }
    await updateEnvFile(
      envPath(context.root, lookup(fulfillment.contract)),
      fulfillment.contractKey,
      value,
    );
  }
  if (fulfills.length === 0 && envFile && envKey) {
    if (!value) {
      return { success: false, error: `No output to fulfill "${envKey}"` };
    }
    await updateEnvFile(resolve(context.root, envFile), envKey, value);
  }

  return { success: true };
};

export default runExecutor;
