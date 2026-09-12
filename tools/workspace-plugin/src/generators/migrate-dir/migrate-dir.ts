import { formatFiles, logger, updateJson, type Tree } from '@nx/devkit';
import { execSync } from 'node:child_process';
import * as path from 'path';
import type { MigrateDirGeneratorSchema } from './schema';

function projectJson(to: string, name: string, kind: 'app' | 'lib' | 'tool'): object {
  const schemaDepth = to
    .split('/')
    .map(() => '..')
    .join('/');
  const base = {
    $schema: `${schemaDepth}/node_modules/nx/schemas/project-schema.json`,
    name,
    sourceRoot: to,
  };
  if (kind === 'app') {
    return {
      ...base,
      projectType: 'application',
      tags: ['type:app', `scope:${name}`],
      targets: {
        'test-unit': {
          executor: '@nx/vitest:test',
          options: { config: '{projectRoot}/vitest.config.ts' },
          inputs: ['default'],
          cache: true,
        },
        typecheck: {
          executor: '@nx/js:tsc',
          options: { tsconfig: '{projectRoot}/tsconfig.json' },
          cache: true,
        },
        lint: { executor: '@nx/eslint:lint', cache: true },
      },
    };
  }
  if (kind === 'lib') {
    return {
      ...base,
      projectType: 'library',
      tags: ['type:lib', `scope:${name}`],
      targets: {
        typecheck: {
          executor: '@nx/js:tsc',
          options: { tsconfig: '{projectRoot}/tsconfig.json' },
          cache: true,
        },
        lint: { executor: '@nx/eslint:lint', cache: true },
      },
    };
  }
  return { ...base, projectType: 'application', tags: ['type:tool', `scope:${name}`] };
}

export async function migrateDirGenerator(tree: Tree, options: MigrateDirGeneratorSchema) {
  const { from, to, kind } = options;
  if (!['app', 'lib', 'tool'].includes(kind)) {
    throw new Error(`kind must be app|lib|tool (got "${kind}")`);
  }
  const name = path.basename(to);
  if (!options.skipMove) {
    execSync(`git mv ${from} ${to}`, { stdio: 'inherit' });
  }
  const packageName = kind === 'lib' ? `@inference/${name}` : name;
  tree.write(
    path.join(to, 'package.json'),
    JSON.stringify({ name: packageName, version: '0.0.1', private: true }, null, 2) + '\n'
  );
  tree.write(path.join(to, 'project.json'), JSON.stringify(projectJson(to, name, kind), null, 2) + '\n');
  if (kind === 'lib' && tree.exists('tsconfig.base.json')) {
    updateJson(tree, 'tsconfig.base.json', (json) => {
      json.compilerOptions ??= {};
      json.compilerOptions.paths ??= {};
      json.compilerOptions.paths[`@inference/${name}`] = [`${to}/src/index.ts`];
      return json;
    });
  }
  await formatFiles(tree);
  logger.info(
    `Moved ${from} -> ${to} as ${name}. Next: fix imports, add tsconfig/tests as needed, npm install.`
  );
}

export default migrateDirGenerator;
