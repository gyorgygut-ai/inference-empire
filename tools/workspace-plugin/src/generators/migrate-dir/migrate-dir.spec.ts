import { createTreeWithEmptyWorkspace } from '@nx/devkit/testing';
import type { Tree } from '@nx/devkit';

import { migrateDirGenerator } from './migrate-dir';

describe('migrate-dir generator', () => {
  let tree: Tree;

  beforeEach(() => {
    tree = createTreeWithEmptyWorkspace();
    tree.write('legacy/app/src/index.ts', 'export {};\n');
  });

  it('writes package and project configs at the target', async () => {
    await migrateDirGenerator(tree, {
      from: 'legacy/app',
      to: 'apps/demo-app',
      kind: 'app',
      skipMove: true,
    });
    expect(tree.exists('apps/demo-app/package.json')).toBe(true);
    const project = JSON.parse(tree.read('apps/demo-app/project.json', 'utf-8'));
    expect(project.name).toBe('demo-app');
    expect(project.tags).toEqual(['type:app', 'scope:demo-app']);
    expect(project.targets['test-unit'].executor).toBe('@nx/vitest:test');
  });

  it('rejects unknown kinds', async () => {
    await expect(
      migrateDirGenerator(tree, {
        from: 'legacy/app',
        to: 'apps/demo-app',
        // @ts-expect-error testing invalid input
        kind: 'gpu',
        skipMove: true,
      })
    ).rejects.toThrow('app|lib|tool');
  });
});
