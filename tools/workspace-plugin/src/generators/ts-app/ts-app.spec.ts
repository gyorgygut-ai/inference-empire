import { createTreeWithEmptyWorkspace } from '@nx/devkit/testing';
import type { Tree } from '@nx/devkit';

import { tsAppGenerator } from './ts-app';

describe('ts-app generator', () => {
  let tree: Tree;

  beforeEach(() => {
    tree = createTreeWithEmptyWorkspace();
  });

  it('scaffolds package, project and configs', async () => {
    await tsAppGenerator(tree, { name: 'demo-app' });
    expect(tree.exists('apps/demo-app/package.json')).toBe(true);
    expect(tree.exists('apps/demo-app/project.json')).toBe(true);
    expect(tree.exists('apps/demo-app/tsconfig.json')).toBe(true);
    expect(tree.exists('apps/demo-app/vitest.config.ts')).toBe(true);
    expect(tree.exists('apps/demo-app/src/index.ts')).toBe(true);
    const project = JSON.parse(tree.read('apps/demo-app/project.json', 'utf-8'));
    expect(project.name).toBe('demo-app');
    expect(project.tags).toEqual(['type:app', 'scope:demo-app']);
  });

  it('rejects invalid names', async () => {
    await expect(tsAppGenerator(tree, { name: 'Bad_Name' })).rejects.toThrow(
      '^[a-z0-9-]+$'
    );
  });
});
