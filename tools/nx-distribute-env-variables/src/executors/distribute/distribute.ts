import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join } from 'node:path';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import type { DistributeExecutorSchema } from './schema';

const BLOCK_START = '# >>> nx-distribute-env-variables managed >>>';
const BLOCK_END = '# <<< nx-distribute-env-variables managed <<<';

function fail(message: string): { success: false } {
  console.error(`[nx-distribute-env-variables] ${message}`);
  return { success: false };
}

function getProjectRootRel(context: ExecutorContext, name: string): string {
  return context.projectsConfigurations?.projects?.[name]?.root ?? '';
}

function expandPath(context: ExecutorContext, projectRootRel: string, raw: string): string {
  const expanded = raw
    .replace('{workspaceRoot}', context.root)
    .replace('{projectRoot}', join(context.root, projectRootRel));
  return isAbsolute(expanded) ? expanded : join(context.root, expanded);
}

function parseDotenv(content: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.length === 0 || trimmed.startsWith('#')) {
      continue;
    }
    const eq = trimmed.indexOf('=');
    if (eq === -1) {
      continue;
    }
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'")))
    ) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

function configPrefix(target: string): string {
  return target.split(':')[0].toUpperCase().replace(/-/g, '_');
}

function readOwnEnvNames(contextRoot: string, projectRootRel: string, targetName: string): string[] | null {
  try {
    const raw = readFileSync(join(contextRoot, projectRootRel, 'project-targets.json'), 'utf8');
    const parsed = JSON.parse(raw) as { targets?: Array<{ name?: unknown; env?: unknown; dependsOn?: unknown }> };
    const entry = (parsed.targets ?? []).find((t) => t.name === targetName);
    if (!entry || !Array.isArray(entry.env)) {
      return null;
    }
    return entry.env.filter((e): e is string => typeof e === 'string');
  } catch {
    return null;
  }
}

function ownDependsOn(contextRoot: string, projectRootRel: string, targetName: string): string[] {
  try {
    const raw = readFileSync(join(contextRoot, projectRootRel, 'project-targets.json'), 'utf8');
    const parsed = JSON.parse(raw) as { targets?: Array<{ name?: unknown; dependsOn?: unknown }> };
    const entry = (parsed.targets ?? []).find((t) => t.name === targetName);
    if (!entry || !Array.isArray(entry.dependsOn)) {
      return [];
    }
    return entry.dependsOn.filter((d): d is string => typeof d === 'string');
  } catch {
    return [];
  }
}

function stripManagedBlock(content: string): { outside: string; hadBlock: boolean } {
  const lines = content.split('\n');
  const outside: string[] = [];
  let inside = false;
  let hadBlock = false;
  for (const line of lines) {
    if (line.trim() === BLOCK_START) {
      inside = true;
      hadBlock = true;
      continue;
    }
    if (line.trim() === BLOCK_END) {
      inside = false;
      continue;
    }
    if (!inside) {
      outside.push(line);
    }
  }
  return { outside: outside.join('\n'), hadBlock };
}

const runExecutor: PromiseExecutor<DistributeExecutorSchema> = async (
  _options,
  context: ExecutorContext
) => {
  const projectName = context.projectName ?? '';
  const targetName = context.targetName ?? '';
  if (!projectName || !targetName) {
    return fail('missing project or target in executor context');
  }
  const projectRootRel = getProjectRootRel(context, projectName);
  if (!projectRootRel) {
    return fail(`unknown project ${projectName}`);
  }
  const bareNames = readOwnEnvNames(context.root, projectRootRel, targetName);
  if (bareNames === null) {
    return fail(`entry "${targetName}" with env list not found in ${projectRootRel}/project-targets.json`);
  }
  const collected: Record<string, string> = {};
  for (const dep of ownDependsOn(context.root, projectRootRel, targetName)) {
    const sep = dep.indexOf(':');
    if (sep === -1) {
      continue;
    }
    const depProject = dep.slice(0, sep);
    const depTarget = dep.slice(sep + 1);
    if (depProject === projectName) {
      continue;
    }
    const depRootRel = getProjectRootRel(context, depProject);
    const depTargets = context.projectsConfigurations?.projects?.[depProject]?.targets as
      | Record<string, { outputs?: unknown }>
      | undefined;
    const outputs = depTargets?.[depTarget]?.outputs;
    if (!Array.isArray(outputs)) {
      continue;
    }
    const prefix = configPrefix(depTarget);
    for (const output of outputs) {
      if (typeof output !== 'string' || !output.endsWith('.env')) {
        continue;
      }
      const artifact = expandPath(context, depRootRel, output);
      if (!existsSync(artifact)) {
        return fail(`producer artifact missing: ${artifact}`);
      }
      const values = parseDotenv(readFileSync(artifact, 'utf8'));
      for (const bare of bareNames) {
        if (!(bare in values)) {
          return fail(`producer artifact ${artifact} lacks ${bare}`);
        }
        collected[`${prefix}_${bare}`] = values[bare];
      }
    }
  }
  const fileName = `.env.${targetName.replace(/:/g, '-')}`;
  const consumerFile = join(context.root, projectRootRel, fileName);
  mkdirSync(dirname(consumerFile), { recursive: true });
  const body = Object.keys(collected)
    .sort()
    .map((key) => `${key}=${collected[key]}`)
    .join('\n');
  writeFileSync(consumerFile, body.length > 0 ? `${body}\n` : '');
  const localFile = join(context.root, projectRootRel, '.env.local');
  const existing = existsSync(localFile) ? readFileSync(localFile, 'utf8') : '';
  const { outside } = stripManagedBlock(existing);
  const outsideValues = parseDotenv(outside);
  for (const key of Object.keys(collected)) {
    if ((outsideValues[key] ?? '') !== '') {
      return fail(`${key} is defined outside the managed block; remove it so distribution owns the key`);
    }
    if ((process.env[key] ?? '') !== '') {
      console.warn(`[nx-distribute-env-variables] ${key} is set in process env and shadows rotation`);
    }
  }
  const block = body.length > 0 ? `${BLOCK_START}\n${body}\n${BLOCK_END}\n` : '';
  const merged = outside.endsWith('\n') || outside.length === 0 ? `${outside}${block}` : `${outside}\n${block}`;
  writeFileSync(localFile, merged);
  return { success: true };
};

export default runExecutor;
