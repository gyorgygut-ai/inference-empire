import sys, time, json, requests
sys.path.insert(0, '.')
from datetime import datetime

ART = 'workers/verification/artifacts'
TS = datetime.now().strftime('%Y%m%d_%H%M%S')

def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)

def main():
    import apps.gpu_workers.krea2.worker_beam_tq_krea2_ref2img as m
    
    log('putting beam krea2 task...')
    task = m.dispatch.put(prompt='a red square', seed=7)
    if not task:
        log('ERROR: dispatch.put returned None')
        sys.exit(1)
    log(f'put OK task={task.id}')
    
    t0 = time.time()
    last_status = None
    while time.time() - t0 < 600:
        s = str(task.status())
        elapsed = int(time.time() - t0)
        if s != last_status:
            log(f'status={s} elapsed={elapsed}s')
            last_status = s
        
        if s == 'COMPLETE':
            out = task.result()
            url = out['artifact']['presigned_url']
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            p = f'{ART}/beam_krea2_{TS}.png'
            with open(p, 'wb') as f:
                f.write(r.content)
            log(f'SAVED {p}')
            return True
        
        if s in ('ERROR', 'TIMEOUT', 'CANCELLED'):
            log(f'ERROR task ended with status={s}')
            return False
        
        if s == 'PENDING' and elapsed > 300:
            log(f'STUCK PENDING {elapsed}s no container assigned')
            return False
        
        time.sleep(10)
    
    log('ERROR: 600s deadline exceeded')
    return False

if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)
