import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { parse } from 'dotenv';
import type { PromiseExecutor } from '@nx/devkit';
import { runCommandCapture } from '@inference/workspace-plugin';
import { updateEnvFile } from '../../../../update-env-file.ts';
import type { RunCommandExecutorSchema } from './schema';

const runExecutor: PromiseExecutor<RunCommandExecutorSchema> = async (options, context) => {
  // `dependsOn` option forwarding applies the dependent target's options as
  // overrides, including command/args/envKey. Only `envFile` is shared across
  // the chain, so keep the target's own execution options.
  const own = (context.target?.options ?? {}) as Partial<RunCommandExecutorSchema>;
  const command = own.command ?? options.command;
  const args = own.args ?? options.args ?? '';
  const env = options.env ?? {};
  const envFile = options.envFile ?? own.envFile;
  const envKey = own.envKey ?? options.envKey;
  const cwd = own.cwd ?? options.cwd;
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
      if (line && envFile && envKey) {
        written = updateEnvFile(envFile, envKey, line);
      }
    },
    { ...inherited, ...env },
  );

  await written;
  return { success: success && (!envKey || value !== null) };
};

export default runExecutor;
