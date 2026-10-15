import { spawn } from 'child_process';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { resolve, dirname, isAbsolute } from 'path';
import type { PromiseExecutor } from '@nx/devkit';
import type { RunInjectedCommandExecutorSchema } from './schema';

const resolveToken = (str: string, root: string, projectRoot?: string): string => {
  return str.replace(/{workspaceRoot}/g, root).replace(/{projectRoot}/g, projectRoot ?? '');
};

const runExecutor: PromiseExecutor<RunInjectedCommandExecutorSchema> = async (options, context) => {
  const projectRoot = (context as any).projectName ? resolve(context.root, context.cwd) : context.cwd;
  const rawCwd = resolveToken(options.cwd ?? context.cwd, context.root, projectRoot);
  const cwd = isAbsolute(rawCwd) ? rawCwd : resolve(context.root, rawCwd);
  const timeoutMs = options.timeout ?? 30000;
  const envVars: Record<string, string> = {};

  for (const item of options.inject) {
    let fullCmd = resolveToken(item.command, context.root, projectRoot);
    if (item.args?.length) {
      fullCmd += ' ' + item.args.map(a => resolveToken(a, context.root, projectRoot)).join(' ');
    }

    const { stdout, code } = await new Promise<{ stdout: string; code: number | null }>((resolve, reject) => {
      const child = spawn(fullCmd, { cwd, shell: true, stdio: 'pipe' });
      let stdout = '';
      child.stdout.on('data', d => stdout += d);
      child.on('close', code => resolve({ stdout, code }));
      child.on('error', reject);
      setTimeout(() => { child.kill(); reject(new Error('timeout')); }, timeoutMs);
    });

    if (code !== 0) return { success: false };
    const val = stdout.trim().split('\n').map(l => l.trim()).filter(Boolean).pop() ?? '';
    envVars[item.env] = val;
    if (item.artifact) {
      const rawArtifact = resolveToken(item.artifact, context.root, projectRoot);
      const p = isAbsolute(rawArtifact) ? rawArtifact : resolve(context.root, rawArtifact);
      const dir = dirname(p);
      if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
      writeFileSync(p, val);
    }
  }

  // The main command is long-lived on continuous targets: only cap it when
  // `timeout` is explicitly configured. Inject scripts above keep the default.
  // One-shot (artifact set): pipe + stream + capture last line → artifact.
  // Continuous (no artifact): inherit, run until exit, as before.
  if (options.artifact === undefined) {
    return new Promise<{ success: boolean }>(resolve => {
      const child = spawn(options.command, { cwd, shell: true, env: { ...process.env, ...envVars }, stdio: 'inherit' });
      child.on('close', c => resolve({ success: c === 0 }));
      child.on('error', () => resolve({ success: false }));
      if (options.timeout !== undefined) {
        setTimeout(() => { child.kill(); resolve({ success: false }); }, timeoutMs);
      }
    });
  }
  return new Promise<{ success: boolean }>(res => {
    const child = spawn(options.command, { cwd, shell: true, env: { ...process.env, ...envVars }, stdio: ['inherit', 'pipe', 'pipe'] });
    let stdout = '';
    child.stdout?.on('data', (d: Buffer) => { process.stdout.write(d); stdout += d.toString('utf8'); });
    child.stderr?.on('data', (d: Buffer) => { process.stderr.write(d); });
    child.on('close', c => {
      if (c !== 0) { res({ success: false }); return; }
      const lines = stdout.split('\n').map(l => l.trim()).filter(Boolean);
      const value = lines.length ? (lines[lines.length - 1] as string) : '';
      const rawArtifact = resolveToken(options.artifact as string, context.root, projectRoot);
      const p = isAbsolute(rawArtifact) ? rawArtifact : resolve(context.root, rawArtifact);
      const dir = dirname(p);
      if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
      writeFileSync(p, value);
      res({ success: true });
    });
    child.on('error', () => res({ success: false }));
    setTimeout(() => { child.kill(); res({ success: false }); }, options.timeout ?? 600000);
  });
};

export default runExecutor;
