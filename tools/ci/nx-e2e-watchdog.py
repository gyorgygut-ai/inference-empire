"""Line-buffered watchdog for `nx run <project>:test-e2e`.
Idempotent: safe to re-run; overwrites log file atomically per invocation.
Usage: python tools/ci/nx-e2e-watchdog.py <project> <logfile>
  [--silence 180] [--hard 900] -- <nx args...>
Kills on: 3 identical loader warnings in 60s, silence limit, hard limit.
Writes KILL_REASON trailer into log on kill. Exit 0 only if child exit 0.
"""
from __future__ import annotations

import collections
import subprocess
import sys
import threading
import time

FATAL_SUBSTRINGS = (
    "Cannot use import statement outside a module",
)

def main() -> int:
    args = sys.argv[1:]
    if len(args) < 2 or "--" not in args:
        print("usage: nx-e2e-watchdog.py <project> <logfile> [--silence S] [--hard H] -- <cmd...>", flush=True)
        return 2
    project = args[0]
    logfile = args[1]
    rest = args[2:]
    silence_limit = 180.0
    hard_limit = 900.0
    cmd_start = 0
    i = 0
    while i < len(rest):
        if rest[i] == "--silence":
            silence_limit = float(rest[i + 1])
            i += 2
        elif rest[i] == "--hard":
            hard_limit = float(rest[i + 1])
            i += 2
        elif rest[i] == "--":
            cmd_start = i + 1
            break
        else:
            i += 1
    cmd = rest[cmd_start:]
    if not cmd:
        print("no command", flush=True)
        return 2
    start = time.time()
    last_out = [start]
    recent = collections.deque(maxlen=10)
    recent_ts: collections.deque[float] = collections.deque(maxlen=10)
    kill_reason = [""]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    child_out = proc.stdout
    assert child_out is not None
    with open(logfile, "w", buffering=1) as lf:
        lf.write(f"WATCHDOG project={project} cmd={' '.join(cmd)} silence={silence_limit} hard={hard_limit}\n")

        def pump() -> None:
            for line in child_out:
                now = time.time()
                last_out[0] = now
                lf.write(line)
                s = line.strip()
                recent.append(s)
                recent_ts.append(now)
                counts: dict[str, int] = {}
                for r, ts in zip(recent, recent_ts):
                    if any(f in r for f in FATAL_SUBSTRINGS) and now - ts < 60:
                        counts[r] = counts.get(r, 0) + 1
                if any(c >= 3 for c in counts.values()):
                    kill_reason[0] = f"KILL_REASON=loader-warning-loop project={project} after={now-start:.0f}s"
                    lf.write(kill_reason[0] + "\n")
                    proc.kill()
                    return
        t = threading.Thread(target=pump, daemon=True)
        t.start()
        rc = None
        while True:
            try:
                rc = proc.wait(timeout=5)
                break
            except subprocess.TimeoutExpired:
                now = time.time()
                if now - start > hard_limit:
                    kill_reason[0] = f"KILL_REASON=hard-timeout project={project} limit={hard_limit} elapsed={now-start:.0f}s"
                    with open(logfile, "a") as lf2:
                        lf2.write(kill_reason[0] + "\n")
                    proc.kill()
                    try:
                        proc.wait(timeout=10)
                    except Exception:
                        proc.terminate()
                    return 124
                if now - last_out[0] > silence_limit:
                    kill_reason[0] = f"KILL_REASON=silence project={project} silence_limit={silence_limit} elapsed={now-start:.0f}s"
                    with open(logfile, "a") as lf2:
                        lf2.write(kill_reason[0] + "\n")
                    proc.kill()
                    try:
                        proc.wait(timeout=10)
                    except Exception:
                        proc.terminate()
                    return 125
        t.join(timeout=10)
    if kill_reason[0]:
        return 126
    return rc if rc is not None else 1

if __name__ == "__main__":
    sys.exit(main())
