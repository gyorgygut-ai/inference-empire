import { createTreeWithEmptyWorkspace } from '@nx/devkit/testing';
import type { Tree } from '@nx/devkit';

import { gpuFamilyGenerator, toModelTag, toTitle } from './gpu-family';

describe('gpu-family generator', () => {
  let tree: Tree;

  beforeEach(() => {
    tree = createTreeWithEmptyWorkspace();
  });

  it('scaffolds apps/<family>/ workers, shared logic and contract', async () => {
    await gpuFamilyGenerator(tree, { family: 'demo_fam' });
    expect(tree.exists('apps/demo_fam/__init__.py')).toBe(true);
    expect(tree.exists('apps/demo_fam/tests/__init__.py')).toBe(true);
    expect(tree.exists('apps/demo_fam/tests/test_demo_fam.py')).toBe(true);
    expect(tree.exists('apps/demo_fam/shared/worker_demo_fam.py')).toBe(true);
    expect(tree.exists('apps/demo_fam/shared/contract_demo_fam.json')).toBe(false);
    expect(tree.exists('packages/contracts/demo_fam/contract.json')).toBe(true);
    expect(tree.exists('apps/demo_fam/project.json')).toBe(true);
    const project = JSON.parse(
      tree.read('apps/demo_fam/project.json', 'utf-8')
    );
    expect(project.name).toBe('gpu-workers-demo-fam');
    expect(project.tags).toContain('model:demo-fam');
  });

  it('rejects invalid family names', async () => {
    await expect(gpuFamilyGenerator(tree, { family: 'Bad-Name' })).rejects.toThrow(
      '^[a-z0-9_]+$'
    );
  });

  it('derives tags and titles', () => {
    expect(toModelTag('demo_fam')).toBe('demo-fam');
    expect(toTitle('demo-fam')).toBe('DemoFam');
  });
});
