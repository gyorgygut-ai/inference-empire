#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process';

function fail(msg: string): never {
  console.error(`[get-modal-url] ${msg}`);
  process.exit(1);
}

const appName = process.argv[2];
const fnName = process.argv[3];
if (!appName || !fnName) {
  fail('usage: get-modal-url.ts <app-name> <function-name>');
}

const python = process.env.MODAL_PYTHON ?? 'python3';
const script = [
  'import os, modal',
  'print(modal.Function.from_name(os.environ["MODAL_URL_APP"], os.environ["MODAL_URL_FN"]).get_web_url() or "None")',
].join('\n');

let out: string;
try {
  out = execFileSync(python, ['-c', script], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'inherit'],
    env: { ...process.env, MODAL_URL_APP: appName, MODAL_URL_FN: fnName },
  });
} catch {
  fail(`modal lookup failed (interpreter: ${python})`);
}

const url = out
  .trim()
  .split('\n')
  .at(-1)?.trim();
if (!url || url === 'None') {
  fail(`no web url for ${appName}/${fnName} (app not deployed or function is not a web endpoint)`);
}
console.log(url);
