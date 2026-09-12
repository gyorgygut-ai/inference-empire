import { formatFiles, generateFiles, logger, type Tree } from '@nx/devkit';
import * as path from 'path';
import type { TsAppGeneratorSchema } from './schema';

export async function tsAppGenerator(tree: Tree, options: TsAppGeneratorSchema) {
  const { name } = options;
  if (!/^[a-z0-9-]+$/.test(name)) {
    throw new Error(`name must match ^[a-z0-9-]+$ (got "${name}")`);
  }
  generateFiles(tree, path.join(__dirname, 'files'), '.', {
    name,
    scope: options.scope ?? name,
  });
  await formatFiles(tree);
  logger.info(`Scaffolded apps/${name}. Next: npm install, implement src/, add tests/.`);
}

export default tsAppGenerator;
