import { spawn } from 'child_process';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { resolve, dirname, isAbsolute } from 'path';
import type { PromiseExecutor } from '@nx/devkit';
import type { RunCommandWithArtifactExecutorSchema } from './schema';

const resolveToken = (str: string, root: string, projectRoot?: string): string => {
  return str.replace(/{workspaceRoot}/g, root).replace(/{projectRoot}/g, projectRoot ?? '');
};

const runExecutor: PromiseExecutor<RunCommandWithArtifactExecutorSchema> = async (options, context) => {
  const ctx = context as unknown as {
    projectName?: string;
    projectsConfigurations?: { projects?: Record<string, { root?: string }> };
  };
  const projectRoot = ctx.projectName
    ? ctx.projectsConfigurations?.projects?.[ctx.projectName]?.root
    : undefined;
  const rawCwd = resolveToken(options.cwd ?? context.cwd, context.root, projectRoot);
  const cwd = isAbsolute(rawCwd) ? rawCwd : resolve(context.root, rawCwd);
  const timeoutMs = options.timeout ?? 120000;

  // Build full command with args
  const fullCmd = [resolveToken(options.command, context.root, projectRoot), ...(options.args?.map(a => resolveToken(a, context.root, projectRoot)) ?? [])].join(' ');

  const { stdout, code } = await new Promise<{ stdout: string; code: number | null }>((resolve, reject) => {
    const child = spawn(fullCmd, { cwd, shell: true, stdio: 'pipe' });
    let stdout = '';
    child.stdout.on('data', d => stdout += d);
    child.on('close', code => resolve({ stdout, code }));
    child.on('error', reject);
    setTimeout(() => { child.kill(); reject(new Error('timeout')); }, timeoutMs);
  });

  if (code !== 0) return { success: false };

  // Write artifact
  const lines = stdout.split('\n').map(l => l.trim()).filter(Boolean);
  const value = lines.length ? lines[lines.length - 1] : '';
  const rawArtifact = resolveToken(options.artifact, context.root, projectRoot);
  const artifactPath = isAbsolute(rawArtifact) ? rawArtifact : resolve(context.root, rawArtifact);
  const artifactDir = dirname(artifactPath);
  if (!existsSync(artifactDir)) mkdirSync(artifactDir, { recursive: true });
  writeFileSync(artifactPath, value, { encoding: 'utf8' });

  return { success: true };
};

export default runExecutor;