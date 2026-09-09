import time, subprocess, sys, threading

iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
print(f'[LAUNCH] started at {iso}', flush=True)

import workers.krea2.worker_beam_tq_krea2_ref2img as worker_mod
task = worker_mod.dispatch.put(prompt='a red square', seed=7)
print(f'[LAUNCH] task.put done', flush=True)

stop = False
last_lines = []
def poll():
    global stop, last_lines
    t0 = time.time()
    while not stop:
        p = subprocess.run(
            ['beam', 'logs', '--stub-id', 'krea2-ref2img-worker'],
            capture_output=True, text=True, check=False
        )
        out = p.stdout + p.stderr
        lines = out.splitlines()
        new = [l for l in lines if l not in last_lines]
        if new:
            tags = [l for l in new if any(t in l for t in ['[INIT]','[REQ]','[GEN]','[R2]','[OK]','[ERR]'])]
            errs = [l for l in new if '[ERR]' in l]
            if errs:
                print('\n'.join(errs), flush=True)
                print('[FAIL] error in worker logs', flush=True)
                stop = True
                return
            if tags:
                print('\n'.join(tags), flush=True)
            last_lines = lines
        elapsed = int(time.time() - t0)
        print(f'[WAIT] still running... {elapsed}s', flush=True)
        time.sleep(10)

t = threading.Thread(target=poll, daemon=True)
t.start()
try:
    out = task.result(wait=True)
    if out is None:
        print('[FAIL] beam task returned None - check beam logs', flush=True)
        sys.exit(1)
    print(f'[OUT] {out}', flush=True)
    if 'artifact' not in out:
        print(f"[FAIL] missing 'artifact' key in output: {out}", flush=True)
        sys.exit(1)
    url = out['artifact']['presigned_url']
    from workers.artifact_check import artifact_exists
    ok = artifact_exists(url)
    print(f'[OK] artifact_exists={ok} url={url}', flush=True)
    sys.exit(0 if ok else 1)
except Exception as e:
    print(f'[FAIL] {type(e).__name__}: {e}', flush=True)
    sys.exit(1)
finally:
    stop = True
    t.join(timeout=5)
