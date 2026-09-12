import {
  formatFiles,
  generateFiles,
  logger,
  updateJson,
  type Tree,
} from '@nx/devkit';
import * as path from 'path';
import type { TsLibGeneratorSchema } from './schema';

export async function tsLibGenerator(tree: Tree, options: TsLibGeneratorSchema) {
  const { name } = options;
  if (!/^[a-z0-9-]+$/.test(name)) {
    throw new Error(`name must match ^[a-z0-9-]+$ (got "${name}")`);
  }
  generateFiles(tree, path.join(__dirname, 'files'), '.', {
    name,
    scope: options.scope ?? name,
  });
  const alias = `@inference/${name}`;
  if (tree.exists('tsconfig.base.json')) {
    updateJson(tree, 'tsconfig.base.json', (json) => {
      json.compilerOptions ??= {};
      json.compilerOptions.paths ??= {};
      json.compilerOptions.paths[alias] = [`packages/${name}/src/index.ts`];
      return json;
    });
  }
  await formatFiles(tree);
  logger.info(`Scaffolded packages/${name} (import as ${alias}). Next: npm install, implement src/.`);
}

export default tsLibGenerator;
