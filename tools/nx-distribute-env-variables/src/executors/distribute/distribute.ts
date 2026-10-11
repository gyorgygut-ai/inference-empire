import { existsSync, readFileSync } from 'node:fs';
import { isAbsolute, join } from 'node:path';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import type { DistributeExecutorSchema } from './schema';

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

function depPrefix(depProject: string, depTarget: string): string {
  const config = configPrefix(depTarget);
  const proj = depProject.toUpperCase().replace(/-/g, '_');
  if (config === proj || config.startsWith(`${proj}_`)) {
    return config;
  }
  return `${proj}_${config}`;
}

function readOwnEnvNamesFromMerged(
  context: ExecutorContext,
  projectName: string,
  targetName: string
): string[] | null {
  const targets = context.projectsConfigurations?.projects?.[projectName]?.targets as
    | Record<string, { inputs?: unknown }>
    | undefined;
  const inputs = targets?.[targetName]?.inputs;
  if (!Array.isArray(inputs)) {
    return null;
  }
  const names: string[] = [];
  for (const input of inputs) {
    if (
      input !== null &&
      typeof input === 'object' &&
      !Array.isArray(input) &&
      typeof (input as { env?: unknown }).env === 'string'
    ) {
      names.push((input as { env: string }).env);
    }
  }
  return names.length > 0 ? names : null;
}

function ownDependsOnFromMerged(
  context: ExecutorContext,
  projectName: string,
  targetName: string
): string[] {
  const targets = context.projectsConfigurations?.projects?.[projectName]?.targets as
    | Record<string, { dependsOn?: unknown }>
    | undefined;
  const dependsOn = targets?.[targetName]?.dependsOn;
  if (!Array.isArray(dependsOn)) {
    return [];
  }
  const out: string[] = [];
  for (const dep of dependsOn) {
    if (typeof dep === 'string') {
      out.push(dep);
    } else if (
      dep !== null &&
      typeof dep === 'object' &&
      !Array.isArray(dep) &&
      typeof (dep as { target?: unknown }).target === 'string'
    ) {
      const target = (dep as { target: string }).target;
      const projects =
        (dep as { projects?: unknown }).projects === undefined
          ? projectName
          : Array.isArray((dep as { projects: unknown }).projects)
            ? ((dep as { projects: string[] }).projects[0] ?? projectName)
            : ((dep as { projects: string }).projects as string);
      out.push(`${projects}:${target}`);
    }
  }
  return out;
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
  const bareNames = readOwnEnvNamesFromMerged(context, projectName, targetName);
  if (bareNames === null) {
    return fail(`entry "${targetName}" with env list not found in merged Nx config`);
  }
  const collected: Record<string, string> = {};
  for (const dep of ownDependsOnFromMerged(context, projectName, targetName)) {
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
    const prefix = depPrefix(depProject, depTarget);
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
  for (const [key, value] of Object.entries(collected)) {
    if ((process.env[key] ?? '') !== '' && process.env[key] !== value) {
      console.warn(`[nx-distribute-env-variables] ${key} already in process env; overwriting with distributed value`);
    }
    process.env[key] = value;
  }
  return { success: true };
};

export default runExecutor;
