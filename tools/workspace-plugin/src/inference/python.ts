import { readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import {
  createNodesFromFiles,
  type CreateNodes,
  type CreateNodesResult,
  type TargetConfiguration,
} from '@nx/devkit';

export interface PythonWorkerPluginOptions {
  readonly auditTarget?: string;
  readonly lintTarget?: string;
  readonly lintFixTarget?: string;
  readonly buildTarget?: string;
  readonly testTarget?: string;
}

function isFamilyRoot(projectRoot: string): boolean {
  const parts = projectRoot.split('/');
  return parts.length === 2 || (parts.length === 3 && parts[1] === 'workers');
}

function readTests(projectRoot: string, workspaceRoot: string): string[] {
  try {
    return readdirSync(join(workspaceRoot, projectRoot, 'tests')).filter((file) =>
      file.endsWith('.py'),
    );
  } catch {
    return [];
  }
}

function createProject(
  projectRoot: string,
  options: PythonWorkerPluginOptions | undefined,
  workspaceRoot: string,
): CreateNodesResult {
  const tests = readTests(projectRoot, workspaceRoot);
  const hasE2e = tests.some((file) => file.startsWith('test_e2e_'));
  const hasUnit = tests.some((file) => file.startsWith('test_') && !file.startsWith('test_e2e_'));

  const auditTarget = options?.auditTarget ?? 'audit';
  const lintTarget = options?.lintTarget ?? 'lint';
  const lintFixTarget = options?.lintFixTarget ?? 'lint-fix';
  const buildTarget = options?.buildTarget ?? 'build';
  const testTarget = options?.testTarget ?? 'test';

  const testDeps: string[] = [];
  if (hasUnit) {
    testDeps.push('test-unit');
  }
  if (hasE2e) {
    testDeps.push('test-e2e');
  }

  const targets: Record<string, TargetConfiguration> = {
    'audit-uv': {
      executor: '@inference/workspace-plugin:audit-uv',
      options: {},
      inputs: ['default', '{workspaceRoot}/uv.lock'],
      cache: true,
    },
    ruff: {
      executor: '@inference/workspace-plugin:ruff',
      options: { projectRoot },
      cache: true,
    },
    [lintFixTarget]: {
      executor: '@inference/workspace-plugin:ruff',
      options: { projectRoot, fix: true },
      cache: false,
    },
    ty: {
      executor: '@inference/workspace-plugin:ty',
      options: { projectRoot },
      cache: true,
    },
    vulture: {
      executor: '@inference/workspace-plugin:vulture',
      options: { projectRoot },
      cache: true,
    },
    [auditTarget]: { dependsOn: ['audit-uv'] },
    [lintTarget]: { dependsOn: [auditTarget, 'ruff', 'ty', 'vulture'] },
    [buildTarget]: {},
    [testTarget]: { dependsOn: testDeps },
    // verify* dependency lists live in nx.json targetDefaults.
    'verify': {},
    'verify-tier-1-audit': {},
    'verify-tier-2-dev': {},
    'verify-tier-3-deploy': {},
  };

  if (hasUnit) {
    targets['test-unit'] = {
      executor: '@inference/workspace-plugin:pytest',
      options: { projectRoot, mode: 'unit' },
      inputs: ['default'],
      cache: true,
    };
  }
  if (hasE2e) {
    targets['test-e2e'] = {
      executor: '@inference/workspace-plugin:pytest',
      options: { projectRoot, mode: 'e2e' },
      inputs: ['default'],
      cache: false,
    };
  }

  return { projects: { [projectRoot]: { targets } } };
}

export const createNodes: CreateNodes<PythonWorkerPluginOptions> = [
  'apps/**/worker_*.py',
  async (configFiles, options, context) =>
    createNodesFromFiles(
      (configFile, opts, ctx) => {
        const projectRoot = dirname(configFile);
        return isFamilyRoot(projectRoot)
          ? createProject(projectRoot, opts, ctx.workspaceRoot)
          : { projects: {} };
      },
      configFiles,
      options,
      context,
    ),
];

export const createNodesV2 = createNodes;
