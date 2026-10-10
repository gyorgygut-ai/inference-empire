import { existsSync, readdirSync, statSync } from 'node:fs';
import { basename, join } from 'node:path';
import type { ExecutorContext } from '@nx/devkit';

export function getProjectRootRel(context: ExecutorContext): string {
  const name = context.projectName ?? '';
  const proj = context.projectsConfigurations?.projects?.[name];
  return proj?.root ?? '';
}

function walk(dir: string, out: string[] = []): string[] {
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    const s = statSync(p);
    if (s.isDirectory()) walk(p, out);
    else if (s.isFile()) out.push(p);
  }
  return out;
}

export function resolveWorkerFile(
  projectRootAbs: string,
  input: string
): { file: string } | { error: string } {
  const base = basename(input);
  const direct = join(projectRootAbs, base);
  if (existsSync(direct) && statSync(direct).isFile()) return { file: base };
  const hits = walk(projectRootAbs).filter((p) => basename(p) === base);
  if (hits.length === 1) return { file: basename(hits[0]) };
  if (hits.length === 0) return { error: `worker file not found: ${base} under ${projectRootAbs}` };
  return { error: `ambiguous worker filename: ${base} matched ${hits.length} files` };
}
