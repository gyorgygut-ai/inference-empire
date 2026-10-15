#!/usr/bin/env -S npx tsx
import { readFileSync } from 'fs';

function sleepSync(ms: number) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function main() {
  const [inputArg, path] = process.argv.slice(2);
  if (!inputArg || !path) {
    console.error('Usage: wait-for-artifact.ts input <path>');
    process.exit(1);
  }

  const timeoutMs = Number(process.env.WAIT_FOR_ARTIFACT_TIMEOUT_MS ?? '120000');
  const intervalMs = Number(process.env.WAIT_FOR_ARTIFACT_INTERVAL_MS ?? '1000');
  const deadline = Date.now() + timeoutMs;

  // Poll until the artifact exists and is non-empty (matches the tool name).
  for (;;) {
    try {
      const content = readFileSync(path, 'utf-8').trim();
      if (content) {
        console.log(content);
        return;
      }
    } catch {
      // Not yet dropped — keep waiting.
    }
    if (Date.now() >= deadline) {
      console.error(`Timed out waiting for ${path} after ${timeoutMs}ms`);
      process.exit(1);
    }
    sleepSync(intervalMs);
  }
}
main();