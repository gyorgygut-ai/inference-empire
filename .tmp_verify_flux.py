import modal, time, subprocess, sys, threading

iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
app_name = 'flux2-klein9b-worker'
Cls = modal.Cls.from_name(app_name, 'FluxKleinWorker')
call = Cls().generate.spawn(prompt='a red square', seed=7)
print(f'[LAUNCH] spawned at {iso}', flush=True)

stop = False
last_lines = []
def poll():
    global stop, last_lines
    t0 = time.time()
    while not stop:
        p = subprocess.run(
            ['modal', 'app', 'logs', app_name, '--since', iso,
             '--timestamps', '--tail', '200'],
            capture_output=True, text=True, check=False
        )
        lines = p.stdout.splitlines()
        new = [l for l in lines if l not in last_lines]
        if new:
            tags = [l for l in new if any(t in l for t in ['[INIT]','[REQ]','[GEN]','[R2]','[OK]','[ERR]'])]
            errs = [l for l in new if '[ERR]' in l]
            if errs:
                print('\n'.join(errs), flush=True)
                print('[FAIL] error in worker logs', flush=True)
                try:
                    call.get(timeout=1)
                except Exception:
                    pass
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
    out = call.get(timeout=600)
    print(f'[OK] {out}', flush=True)
    sys.exit(0)
except Exception as e:
    print(f'[FAIL] {type(e).__name__}: {e}', flush=True)
    sys.exit(1)
finally:
    stop = True
    t.join(timeout=5)
    subprocess.run(['modal', 'app', 'stop', app_name, '--yes'], check=False)
