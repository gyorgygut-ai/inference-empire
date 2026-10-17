import { existsSync, readFileSync } from 'node:fs';
import { parse as parseDotenv } from 'dotenv';

export interface EnvOptions {
  envFile?: string;
  env?: Record<string, string>;
}

const VAR = /\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))/g;

export function resolveVars(
  values: Record<string, string>,
  source: NodeJS.ProcessEnv,
): Record<string, string> {
  const resolved: Record<string, string> = {};
  for (const [key, value] of Object.entries(values)) {
    resolved[key] = value.replace(VAR, (_, braced: string, bare: string) => source[braced ?? bare] ?? '');
  }
  return resolved;
}

export function buildChildEnv(options: EnvOptions): NodeJS.ProcessEnv {
  const fileEnv =
    options.envFile && existsSync(options.envFile)
      ? parseDotenv(readFileSync(options.envFile))
      : {};
  return { ...process.env, ...fileEnv, ...resolveVars(options.env ?? {}, process.env) };
}
