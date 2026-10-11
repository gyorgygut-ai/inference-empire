import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join } from 'node:path';
import type { ExecutorContext, PromiseExecutor } from '@nx/devkit';
import type { ResolveExecutorSchema } from './schema';

function getProjectRootRel(context: ExecutorContext): string {
  const name = context.projectName ?? '';
  return context.projectsConfigurations?.projects?.[name]?.root ?? '';
}

function resolveOutputPath(context: ExecutorContext, output: string): string {
  const expanded = output
    .replace('{workspaceRoot}', context.root)
    .replace('{projectRoot}', join(context.root, getProjectRootRel(context)));
  return isAbsolute(expanded) ? expanded : join(context.root, expanded);
}

function upsertDotenvLine(content: string, key: string, value: string): string {
  const lines = content.length > 0 ? content.split('\n') : [];
  let found = false;
  const next = lines.map((line) => {
    if (line.trim().startsWith(`${key}=`)) {
      found = true;
      return `${key}=${value}`;
    }
    return line;
  });
  if (!found) {
    next.push(`${key}=${value}`);
  }
  const body = next.join('\n');
  return body.endsWith('\n') ? body : `${body}\n`;
}

function expand(context: ExecutorContext, raw: string): string {
  const expanded = raw
    .replace('{workspaceRoot}', context.root)
    .replace('{projectRoot}', join(context.root, context.projectsConfigurations?.projects?.[context.projectName ?? '']?.root ?? ''));
  return isAbsolute(expanded) ? expanded : join(context.root, expanded);
}

function readEndpointsArtifact(file: string): { appUrl: string; beamUrl: string } | null {
  if (!existsSync(file)) return null;
  try {
    const raw = JSON.parse(readFileSync(file, 'utf8')) as { appUrl?: unknown; beamUrl?: unknown };
    if (typeof raw.appUrl === 'string' && typeof raw.beamUrl === 'string') {
      return { appUrl: raw.appUrl, beamUrl: raw.beamUrl };
    }
    return null;
  } catch {
    return null;
  }
}

const runExecutor: PromiseExecutor<ResolveExecutorSchema> = async (options, context) => {
  if (!options.output) {
    console.error('[nx-distribute-resolved-url] output is required');
    return { success: false };
  }
  let appUrl = process.env.APP_URL ?? '';
  let beamUrl = process.env.BEAM_URL ?? '';
  if ((!appUrl || !beamUrl) && options.endpoints) {
    const artifact = expand(context, options.endpoints);
    const found = readEndpointsArtifact(artifact);
    if (found) {
      if (!appUrl) appUrl = found.appUrl;
      if (!beamUrl) beamUrl = found.beamUrl;
    } else if (!appUrl) {
      console.error(`[nx-distribute-resolved-url] endpoints artifact missing or invalid: ${artifact}`);
    }
  }
  if (!appUrl) appUrl = options.defaultAppUrl ?? '';
  if (!beamUrl) beamUrl = options.defaultBeamUrl ?? appUrl;
  if (!appUrl) {
    console.error('[nx-distribute-resolved-url] APP_URL is not set (set APP_URL env, endpoints artifact, or defaultAppUrl option)');
    return { success: false };
  }
  if (!beamUrl) {
    console.error('[nx-distribute-resolved-url] BEAM_URL is not set');
    return { success: false };
  }
  const out = resolveOutputPath(context, options.output);
  mkdirSync(dirname(out), { recursive: true });
  const existing = existsSync(out) ? readFileSync(out, 'utf8') : '';
  const withApp = upsertDotenvLine(existing, 'APP_URL', appUrl);
  writeFileSync(out, upsertDotenvLine(withApp, 'BEAM_URL', beamUrl));
  process.env['APP_URL'] = appUrl;
  process.env['BEAM_URL'] = beamUrl;
  return { success: true };
};

export default runExecutor;
