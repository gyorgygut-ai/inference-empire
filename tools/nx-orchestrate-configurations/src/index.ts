import { createNodesFromFiles, readJsonFile, type CreateNodesV2 } from '@nx/devkit';
import { dirname } from 'node:path';

function fail(message: string): never {
  throw new Error(`[nx-orchestrate-configurations] ${message}`);
}

function createNodesInternal(
  configFilePath: string,
  _options: unknown,
  _context: unknown,
): { projects: Record<string, { targets: Record<string, unknown> }> } {
  const projectRoot = dirname(configFilePath);
  let raw: Record<string, unknown>;
  try {
    raw = readJsonFile(configFilePath) as Record<string, unknown>;
  } catch {
    fail(`cannot read ${configFilePath}`);
  }
  if (!Array.isArray(raw['targets'])) {
    fail(`${configFilePath} must contain a "targets" array`);
  }
  const targets: Record<string, unknown> = {};
  for (const entry of raw['targets'] as Array<Record<string, unknown>>) {
    if (typeof entry['name'] !== 'string' || (entry['name'] as string).length === 0) {
      fail(`${configFilePath}: every entry needs a non-empty "name"`);
    }
    const target: Record<string, unknown> = {};
    if (entry['executor'] !== undefined) {
      target['executor'] = entry['executor'];
    }
    if (entry['options'] !== undefined) {
      target['options'] = entry['options'];
    }
    const dependsOn = [...((entry['dependsOn'] as string[] | undefined) ?? [])];
    if (dependsOn.length > 0) {
      target['dependsOn'] = dependsOn;
    }
    const inputs: unknown[] = [];
    if (entry['contract'] !== undefined) {
      inputs.push(`{workspaceRoot}/${entry['contract'] as string}`);
    }
    for (const name of ((entry['env'] as string[] | undefined) ?? [])) {
      inputs.push({ env: name });
    }
    for (const input of ((entry['inputs'] as unknown[] | undefined) ?? [])) {
      inputs.push(input);
    }
    if (inputs.length > 0) {
      target['inputs'] = inputs;
    }
    if (entry['outputs'] !== undefined) {
      target['outputs'] = entry['outputs'];
    }
    if (entry['cache'] !== undefined) {
      target['cache'] = entry['cache'];
    }
    targets[entry['name'] as string] = target;
  }
  return { projects: { [projectRoot]: { targets } } };
}

export const createNodesV2: CreateNodesV2 = [
  'apps/*/project-targets.json',
  async (configFiles, options, context) => {
    return await createNodesFromFiles(
      (configFile, opts, ctx) => createNodesInternal(configFile, opts, ctx),
      configFiles,
      options,
      context,
    );
  },
];

export const createNodes = createNodesV2;
