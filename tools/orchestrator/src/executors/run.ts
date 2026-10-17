import { spawn } from 'node:child_process';
import { updateEnvFile } from '../../update-env-file';
import { buildChildEnv, type EnvOptions } from './env';

export interface RunChildOptions extends EnvOptions {
  command: string;
  args?: string[];
  key?: string;
}

export interface RunChildContext {
  cwd: string;
  continuous: boolean;
}

/**
 * Spawn `command` with `args` (no shell). The child env is `process.env` overlaid
 * with the parsed `envFile` and the resolved `env` option. The first stdout line
 * is captured and, when `key` is set, written into `envFile` via `update-env-file`.
 *
 * - continuous: resolves as soon as the value line is captured; the detached child
 *   stays alive so the caller (e.g. a dev server) keeps running.
 * - non-continuous: resolves when the child exits, after the value has been written.
 */
export async function runChild(
  options: RunChildOptions,
  context: RunChildContext,
): Promise<{ success: boolean }> {
  const env = buildChildEnv(options);

  return await new Promise<{ success: boolean }>((resolve) => {
    let settled = false;
    let captured = false;
    let buffer = '';
    let write: Promise<void> = Promise.resolve();

    const finish = (success: boolean): void => {
      if (settled) return;
      settled = true;
      resolve({ success });
    };

    const capture = (line: string): void => {
      if (captured) return;
      captured = true;
      if (options.key && options.envFile) {
        write = updateEnvFile(options.envFile, options.key, line).catch((error: unknown) => {
          console.error(`[orchestrator] failed to write ${options.key}: ${String(error)}`);
          finish(false);
        });
      }
      if (context.continuous) {
        void write.then(() => finish(true));
      }
    };

    const child = spawn(options.command, options.args ?? [], {
      cwd: context.cwd,
      env,
      stdio: ['inherit', 'pipe', 'pipe'],
      detached: process.platform !== 'win32',
    });

    child.stdout?.on('data', (chunk: Buffer) => {
      const text = chunk.toString('utf8');
      process.stdout.write(text);
      if (captured) return;
      buffer += text;
      const newline = buffer.indexOf('\n');
      if (newline !== -1) {
        capture(buffer.slice(0, newline).trim());
        buffer = '';
      }
    });

    child.stderr?.on('data', (chunk: Buffer) => {
      process.stderr.write(chunk);
    });

    child.on('error', (error) => {
      console.error(`[orchestrator] failed to start ${options.command}: ${error.message}`);
      finish(false);
    });

    child.on('close', (code) => {
      if (!captured && buffer.trim().length > 0) {
        capture(buffer.trim());
      }
      void write.then(() => {
        if (settled) return;
        if (context.continuous && !captured) {
          finish(false);
          return;
        }
        finish(code === 0);
      });
    });
  });
}
