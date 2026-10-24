import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { parse } from 'dotenv';
import type { PromiseExecutor } from '@nx/devkit';
import { runCommandCapture } from '@inference/workspace-plugin';
import { updateEnvFile } from '../../../../update-env-file.ts';
import type { RunCommandExecutorSchema } from './schema';

const runExecutor: PromiseExecutor<RunCommandExecutorSchema> = async (options, context) => {
  const own = (context.target?.options ?? {}) as Partial<RunCommandExecutorSchema>;
  const command = own.command ?? options.command;
  const args = own.args ?? options.args ?? '';
  const env = options.env ?? {};
  let envFile = options.envFile ?? own.envFile;
  const envKey = own.envKey ?? options.envKey;
  const cwd = own.cwd ?? options.cwd;
  const needs = own.needs ?? options.needs;
  const fulfills = own.fulfills ?? options.fulfills;
  const taskName = `${context.projectName}:${context.targetName}`;

  if (needs) {
    const contractPath = resolve(
      context.root,
      'packages/contracts',
      `${needs.contract}.contract.ts`
    );
    const mod = await import(contractPath);
    const envFilePath = mod[`${needs.contract}Contract`]?.envFilePath;
    if (envFilePath) {
      envFile = envFilePath(taskName);
    }
  }

  const inherited =
    envFile && existsSync(envFile)
      ? { ...process.env, ...parse(readFileSync(envFile)) }
      : process.env;

  let value: string | null = null;
  let written: Promise<void> = Promise.resolve();

  const success = await runCommandCapture(
    [command, args].filter(Boolean).join(' '),
    cwd ? resolve(context.root, cwd) : context.root,
    (line) => {
      if (value !== null) {
        return;
      }
      value = line;
      if (fulfills) {
        const contractPath = resolve(
          context.root,
          'packages/contracts',
          `${fulfills.contract}.contract.ts`
        );
        import(contractPath).then((mod) => {
          const envFilePath = mod[`${fulfills.contract}Contract`]?.envFilePath;
          if (envFilePath && line) {
            written = updateEnvFile(envFilePath(taskName), fulfills.contractKey, line);
          }
        });
      } else if (line && envFile && envKey) {
        written = updateEnvFile(envFile, envKey, line);
      }
    },
    { ...inherited, ...env },
  );

  await written;
  return { success: success && (!envKey || value !== null) };
};

export default runExecutor;
