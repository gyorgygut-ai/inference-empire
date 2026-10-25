#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';

function fail(msg: string): never {
  console.error(`[get-flash-url] ${msg}`);
  process.exit(1);
}

const args = process.argv.slice(2);
let dir = process.cwd();
const rest: string[] = [];
for (let i = 0; i < args.length; i++) {
  const arg = args[i] ?? '';
  if (arg === '--dir') {
    const value = args[++i];
    if (!value) {
      fail('--dir requires a path');
    }
    dir = resolve(value);
  } else {
    rest.push(arg);
  }
}
const name = rest[0];
if (!name) {
  fail('usage: get-flash-url.ts <endpoint-name> [--dir <flash-project-dir>]');
}

let out: string;
try {
  out = execFileSync('flash', ['undeploy', 'list'], {
    encoding: 'utf8',
    cwd: dir,
    stdio: ['ignore', 'pipe', 'inherit'],
    env: { ...process.env, NO_COLOR: '1' },
  });
} catch {
  fail(`flash undeploy list failed (dir: ${dir})`);
}

const stripAnsi = (s: string): string => s.replace(/\u001b\[[0-9;]*m/g, '');
let endpointId: string | undefined;
for (const line of stripAnsi(out).split('\n')) {
  // rendered line: "● <name> <endpoint-id>"
  const tokens = line.trim().split(/\s+/).filter(Boolean);
  if (tokens.length >= 3 && tokens[0] === '●' && tokens[1] === name) {
    endpointId = tokens[tokens.length - 1];
  }
}
if (!endpointId) {
  fail(`no endpoint named "${name}" in flash undeploy list (dir: ${dir})`);
}
console.log(`https://api.runpod.ai/v2/${endpointId}/infer`);
