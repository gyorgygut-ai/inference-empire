import { readdirSync, readFileSync } from 'node:fs';
import { basename, dirname, join } from 'node:path';
import { createNodesFromFiles, type CreateNodes } from '@nx/devkit';

export interface PythonWorkerPluginOptions {
  readonly auditTarget?: string;
  readonly lintTarget?: string;
  readonly buildTarget?: string;
  readonly testTarget?: string;
  readonly verifyTarget?: string;
}

interface FamilySignals {
  readonly hasImagePipDeps: boolean;
  readonly pythonVersion: string;
  readonly hasUnit: boolean;
  readonly hasE2e: boolean;
}

function readWorkerSources(projectRoot: string, workspaceRoot: string): string[] {
  const dir = join(workspaceRoot, projectRoot);
  let files: string[] = [];
  try {
    files = readdirSync(dir).filter((f) => f.startsWith('worker_') && f.endsWith('.py'));
  } catch {
    return [];
  }
  return files.map((f) => {
    try {
      return readFileSync(join(dir, f), 'utf-8');
    } catch {
      return '';
    }
  });
}

function readTestFiles(projectRoot: string, workspaceRoot: string): string[] {
  try {
    return readdirSync(join(workspaceRoot, projectRoot, 'tests')).filter((f) => f.endsWith('.py'));
  } catch {
    return [];
  }
}

function collectSignals(projectRoot: string, workspaceRoot: string): FamilySignals {
  const sources = readWorkerSources(projectRoot, workspaceRoot);
  const combined = sources.join('\n');
  const tests = readTestFiles(projectRoot, workspaceRoot);
  return {
    hasImagePipDeps: combined.includes('IMAGE_PIP_DEPS'),
    pythonVersion: combined.includes('3.10') ? '3.10' : '3.11',
    hasUnit: tests.some((f) => f.startsWith('test_') && !f.startsWith('test_e2e_')),
    hasE2e: tests.some((f) => f.startsWith('test_e2e_')),
  };
}

function createNodesInternal(
  configFilePath: string,
  options: PythonWorkerPluginOptions | undefined,
  context: { workspaceRoot: string },
): { projects: Record<string, { targets: Record<string, unknown> }> } {
  const projectRoot = dirname(configFilePath);
  const family = basename(projectRoot);
  const signals = collectSignals(projectRoot, context.workspaceRoot);

  const auditTarget = options?.auditTarget ?? 'audit';
  const lintTarget = options?.lintTarget ?? 'lint';
  const buildTarget = options?.buildTarget ?? 'build';
  const testTarget = options?.testTarget ?? 'test';
  const verifyTarget = options?.verifyTarget ?? 'verify';

  const auditDeps = ['audit-uv'];
  if (signals.hasImagePipDeps) {
    auditDeps.push('validate-deps');
  }
  const testDeps: string[] = [];
  if (signals.hasUnit) {
    testDeps.push('test-unit');
  }
  if (signals.hasE2e) {
    testDeps.push('test-e2e');
  }

  const targets: Record<string, unknown> = {
    'audit-uv': {
      executor: 'nx:run-commands',
      options: { command: 'uv pip check', cwd: '.' },
      inputs: ['default', '{workspaceRoot}/uv.lock'],
      cache: true,
    },
    ruff: {
      executor: '@inference/workspace-plugin:ruff',
      options: { family },
      cache: true,
    },
    ty: {
      executor: '@inference/workspace-plugin:ty',
      options: { family },
      cache: true,
    },
    vulture: {
      executor: 'nx:run-commands',
      options: { command: `uv run --locked --group test vulture apps/${family}`, cwd: '.' },
      cache: true,
    },
    [auditTarget]: { dependsOn: auditDeps },
    [lintTarget]: { dependsOn: [auditTarget, 'ruff', 'ty', 'vulture'] },
    [buildTarget]: {},
    [testTarget]: { dependsOn: testDeps },
    [verifyTarget]: { dependsOn: [auditTarget, lintTarget, buildTarget, testTarget], cache: false },
  };

  if (signals.hasImagePipDeps) {
    targets['validate-deps'] = {
      executor: '@inference/workspace-plugin:validate-deps',
      options: { family, python_version: signals.pythonVersion },
      cache: true,
    };
  }
  if (signals.hasUnit) {
    targets['test-unit'] = {
      executor: '@inference/workspace-plugin:pytest',
      options: { family, mode: 'unit' },
      inputs: ['default'],
      cache: true,
    };
  }
  if (signals.hasE2e) {
    targets['test-e2e'] = {
      executor: 'nx:run-commands',
      options: { command: `uv run --locked --group test pytest apps/${family}/tests/ -k "e2e" -q`, cwd: '.' },
      inputs: ['default'],
      cache: false,
    };
  }

  return { projects: { [projectRoot]: { targets } } };
}

export const createNodes: CreateNodes<PythonWorkerPluginOptions> = [
  'apps/*/worker_*.py',
  async (configFiles, options, context) => {
    return await createNodesFromFiles(
      (configFile, opts, ctx) => createNodesInternal(configFile, opts, ctx),
      configFiles,
      options,
      context,
    );
  },
];

export const createNodesV2 = createNodes;
