#!/usr/bin/env -S npx tsx
import { spawn } from 'node:child_process';
import { join } from 'node:path';

const port = Number(process.env.ROUTER_DEV_PORT ?? 5050);
const url = `http://127.0.0.1:${port}`;

async function ready(): Promise<boolean> {
  try {
    await fetch(url);
    return true;
  } catch {
    return false;
  }
}

if (!(await ready())) {
  const child = spawn('npx', ['netlify', 'dev', '--port', String(port)], {
    cwd: join(process.cwd(), 'apps', 'functions'),
    detached: true,
    stdio: 'ignore',
  });
  child.unref();
  for (let attempt = 0; attempt < 120 && !(await ready()); attempt++) {
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}

if (!(await ready())) {
  console.error(`[serve-netlify-functions] router on ${url} did not become ready`);
  process.exit(1);
}

console.log(url);
