import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

export type DeployEndpoints = {
  producer: 'modal' | 'beam' | 'flash';
  worker: string;
  appUrl: string;
  beamUrl: string;
  at: string;
};

export function writeDeployEndpoints(
  workspaceRoot: string,
  projectRootRel: string,
  data: Omit<DeployEndpoints, 'at'>
): string {
  const out = join(workspaceRoot, projectRootRel, 'dist/deploy-endpoints.json');
  mkdirSync(dirname(out), { recursive: true });
  const payload: DeployEndpoints = { ...data, at: new Date().toISOString() };
  writeFileSync(out, `${JSON.stringify(payload, null, 2)}\n`);
  return out;
}

export function readDeployEndpoints(file: string): DeployEndpoints | null {
  try {
    const { readFileSync, existsSync } = require('node:fs') as typeof import('node:fs');
    if (!existsSync(file)) return null;
    const raw = JSON.parse(readFileSync(file, 'utf8')) as Partial<DeployEndpoints>;
    if (typeof raw.appUrl !== 'string' || typeof raw.beamUrl !== 'string') return null;
    return raw as DeployEndpoints;
  } catch {
    return null;
  }
}
