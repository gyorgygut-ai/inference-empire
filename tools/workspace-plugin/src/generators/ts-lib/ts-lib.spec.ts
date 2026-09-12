import { createTreeWithEmptyWorkspace } from '@nx/devkit/testing';
import type { Tree } from '@nx/devkit';

import { tsLibGenerator } from './ts-lib';

describe('ts-lib generator', () => {
  let tree: Tree;

  beforeEach(() => {
    tree = createTreeWithEmptyWorkspace();
  });

  it('scaffolds package, project and path alias', async () => {
    await tsLibGenerator(tree, { name: 'demo-lib' });
    expect(tree.exists('packages/demo-lib/package.json')).toBe(true);
    expect(tree.exists('packages/demo-lib/project.json')).toBe(true);
    expect(tree.exists('packages/demo-lib/tsconfig.json')).toBe(true);
    expect(tree.exists('packages/demo-lib/src/index.ts')).toBe(true);
    const project = JSON.parse(tree.read('packages/demo-lib/project.json', 'utf-8'));
    expect(project.name).toBe('demo-lib');
    expect(project.tags).toEqual(['type:lib', 'scope:demo-lib']);
    if (tree.exists('tsconfig.base.json')) {
      const base = JSON.parse(tree.read('tsconfig.base.json', 'utf-8'));
      expect(base.compilerOptions.paths['@inference/demo-lib']).toEqual([
        'packages/demo-lib/src/index.ts',
      ]);
    }
  });

  it('rejects invalid names', async () => {
    await expect(tsLibGenerator(tree, { name: 'Bad_Name' })).rejects.toThrow(
      '^[a-z0-9-]+$'
    );
  });
});
