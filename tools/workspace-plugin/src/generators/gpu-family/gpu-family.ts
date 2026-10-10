import { formatFiles, generateFiles, logger, type Tree } from '@nx/devkit';
import * as path from 'path';
import type { GpuFamilyGeneratorSchema } from './schema';

export function toModelTag(family: string): string {
  return family.replace(/_/g, '-');
}

export function toTitle(name: string): string {
  return name
    .split(/[-_]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('');
}

export async function gpuFamilyGenerator(tree: Tree, options: GpuFamilyGeneratorSchema) {
  const { family } = options;
  if (!/^[a-z0-9_]+$/.test(family)) {
    throw new Error(`family must match ^[a-z0-9_]+$ (got "${family}")`);
  }
  const contract = options.contract ?? toModelTag(family);
  generateFiles(tree, path.join(__dirname, 'files'), '.', {
    family,
    modelTag: toModelTag(family),
    contractTitle: toTitle(contract),
    pythonVersion: options.pythonVersion ?? '3.11',
  });
  await formatFiles(tree);
  logger.info(
    `Scaffolded family "${family}". Next: fill packages/contracts/${family}/contract.json, ` +
      `implement apps/${family}/shared/worker_${family}.py and apps/${family}/ workers.`
  );
}

export default gpuFamilyGenerator;
