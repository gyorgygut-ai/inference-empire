import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { resolveWorkerFile } from './resolve-worker';

function makeTree(files: string[]): string {
  const dir = mkdtempSync(join(tmpdir(), 'worker-'));
  for (const f of files) {
    const full = join(dir, f);
    mkdirSync(join(full, '..'), { recursive: true });
    writeFileSync(full, '# stub');
  }
  return dir;
}

describe('resolveWorkerFile', () => {
  it('resolves basename in project root', () => {
    const dir = makeTree(['worker_modal_cls_a.py']);
    expect(resolveWorkerFile(dir, 'worker_modal_cls_a.py')).toEqual({ file: 'worker_modal_cls_a.py' });
  });
  it('resolves basename in nested dir to basename', () => {
    const dir = makeTree(['shared/worker_beam_tq_a.py']);
    expect(resolveWorkerFile(dir, 'worker_beam_tq_a.py')).toEqual({ file: 'worker_beam_tq_a.py' });
  });
  it('fails on missing file', () => {
    const dir = makeTree(['other.py']);
    const r = resolveWorkerFile(dir, 'missing.py') as { error: string };
    expect(r.error).toMatch(/not found/);
  });
  it('fails on ambiguous basename', () => {
    const dir = makeTree(['a/worker_x.py', 'b/worker_x.py']);
    const r = resolveWorkerFile(dir, 'worker_x.py') as { error: string };
    expect(r.error).toMatch(/ambiguous/);
  });
});
