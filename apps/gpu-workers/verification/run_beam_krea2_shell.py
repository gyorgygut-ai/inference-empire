import os, pty, select, re, sys, time, json, requests
from datetime import datetime

TS = datetime.now().strftime('%Y%m%d_%H%M%S')
ART = 'workers/verification/artifacts'
os.makedirs(ART, exist_ok=True)

TAG_RE = re.compile(r'\[(INIT|REQ|GEN|R2|OK|ERR)\]')
URL_RE = re.compile(r'https?://[^\s"\'<>]+\.(?:png|jpg|jpeg|webp)')

start = time.time()
last_report = time.time()
logs = []
seen_tags = set()
artifact_url = None
error = None
done = False
prompt_seen = False

def report():
    global last_report
    elapsed = int(time.time() - start)
    print(f'[REPORT {datetime.now().strftime("%H:%M:%S")}] elapsed={elapsed}s tags={sorted(seen_tags)} url={artifact_url} error={error} done={done}', flush=True)
    last_report = time.time()

def parse_output(text):
    global artifact_url, error, done, seen_tags, prompt_seen
    logs.append(text)
    # Check for prompt
    if '>>> ' in text or 'In [1]:' in text or 'Python ' in text:
        prompt_seen = True
    # Check tags
    for m in TAG_RE.finditer(text):
        seen_tags.add(m.group(1))
    # Check URL
    m = URL_RE.search(text)
    if m:
        artifact_url = m.group(0)
    # Check completion/error
    if '[OK]' in text:
        done = True
    if '[ERR]' in text:
        error = text.strip()
        done = True

def send(fd, cmd):
    os.write(fd, (cmd + '\n').encode('utf-8'))

def wait_for_prompt(fd, timeout=300):
    deadline = time.time() + timeout
    buf = b''
    while time.time() < deadline:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            buf += chunk
            text = buf.decode('utf-8', errors='replace')
            parse_output(text)
            # Check for prompt in buffer
            if '>>> ' in text or 'In [1]:' in text:
                return True
        # 30s report
        if time.time() - last_report >= 30:
            report()
    return False

def read_output(fd, timeout=30):
    deadline = time.time() + timeout
    buf = b''
    while time.time() < deadline:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            buf += chunk
    text = buf.decode('utf-8', errors='replace')
    parse_output(text)
    return text

print(f'[START {datetime.now().strftime("%H:%M:%S")}] launching beam shell...', flush=True)

pid, fd = pty.fork()
if pid == 0:
    os.execvp('beam', ['beam', 'shell', 'workers/krea2/worker_beam_tq_krea2_ref2img.py:dispatch'])

# Wait for container to boot and Python prompt
print('[WAIT] waiting for Python prompt (up to 5 min)...', flush=True)
if not wait_for_prompt(fd, timeout=300):
    print('[FAIL] no Python prompt within 5 min', flush=True)
    os.kill(pid, 9)
    sys.exit(1)

report()
print('[READY] Python prompt detected, sending commands...', flush=True)

# Send the 3 commands
send(fd, 'from apps.gpu_workers.krea2.worker_beam_tq_krea2_ref2img import load_deps, generate')
time.sleep(1)
send(fd, 'storage, pipe, runtime_dir, torch_module = load_deps()')
time.sleep(1)
send(fd, 'generate(storage, pipe, runtime_dir, torch_module, prompt="a red square", seed=7)')

# Monitor for completion
monitor_deadline = time.time() + 900  # 15 min
while time.time() < monitor_deadline and not done:
    read_output(fd, timeout=5)
    if time.time() - last_report >= 30:
        report()
    time.sleep(1)

# Final drain
for _ in range(60):
    read_output(fd, timeout=2)
    time.sleep(0.5)

report()

# Download artifact
if artifact_url:
    print(f'[DOWNLOAD] fetching {artifact_url}', flush=True)
    r = requests.get(artifact_url, timeout=120)
    r.raise_for_status()
    p = f'{ART}/beam_krea2_{TS}.png'
    with open(p, 'wb') as f:
        f.write(r.content)
    print(f'[SAVED] {p}', flush=True)
    os.kill(pid, 9)
    sys.exit(0)
else:
    print(f'[FAIL] done={done} error={error} tags={sorted(seen_tags)}', flush=True)
    os.kill(pid, 9)
    sys.exit(1)
