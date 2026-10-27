import { basename, dirname, join } from 'node:path';
import {
  createNodesFromFiles,
  readJsonFile,
  type CreateNodes,
  type CreateNodesResult,
  type TargetConfiguration,
} from '@nx/devkit';

interface ProjectJson {
  readonly targets?: Readonly<Record<string, {
    readonly executor?: string;
    readonly options?: Readonly<Record<string, unknown>>;
  }>>;
}

function createProject(
  configFile: string,
  workspaceRoot: string,
): CreateNodesResult {
  const projectRoot = dirname(configFile);
  const targets: Record<string, TargetConfiguration> = {
    verify: {},
    'verify-tier-1-audit': {},
    'verify-tier-2-dev': {},
    'verify-tier-3-deploy': {},
  };

  if (basename(configFile) === 'project.json') {
    const projectJson = readJsonFile(join(workspaceRoot, configFile)) as ProjectJson;
    const lintCommand = projectJson.targets?.lint?.options?.command;

    if (typeof lintCommand === 'string' && lintCommand.includes('ruff check')) {
      const lintOptions = projectJson.targets?.lint?.options;
      targets['lint-fix'] = {
        executor: 'dotenvx:run-commands',
        options: {
          ...lintOptions,
          command: lintCommand.replace(/\s+--fix\b/g, ''),
          args: `${Array.isArray(lintOptions?.args) ? lintOptions.args.join(' ') : lintOptions?.args ?? ''} --fix`,
          cwd: lintOptions?.cwd ?? '.',
        },
        cache: false,
      };
    }
  }

  return { projects: { [projectRoot]: { targets } } };
}

export const createNodes: CreateNodes = [
  '**/project.json',
  async (configFiles, _options, context) =>
    createNodesFromFiles(
      (configFile, _opts, ctx) => createProject(configFile, ctx.workspaceRoot),
      configFiles,
      _options,
      context,
    ),
];

export const createNodesV2 = createNodes;
