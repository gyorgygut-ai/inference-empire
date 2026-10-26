#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { resolve } from 'node:path';

function fail(msg: string): never {
  console.error(`[get-beam-url] ${msg}`);
  process.exit(1);
}

const appName = process.argv[2];

function token(): string {
  const envToken = process.env.BEAM_TOKEN;
  if (envToken) {
    return envToken;
  }
  const ini = resolve(homedir(), '.beam/config.ini');
  if (existsSync(ini)) {
    const match = readFileSync(ini, 'utf8').match(/^\s*token\s*=\s*(.+)$/m);
    if (match?.[1]) {
      return match[1].trim();
    }
  }
  fail('no BEAM_TOKEN env var and no token in ~/.beam/config.ini');
}

let deployments: Array<{ id: string; name: string; active: boolean; version: number }>;
try {
  const out = execFileSync('beam', ['deployment', 'list', '--format', 'json', '--limit', '100'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'inherit'],
  });
  deployments = JSON.parse(out.replace(/\u001b\[[0-9;]*m/g, ''));
} catch {
  fail('beam deployment list failed');
}

const latest = deployments
  .filter((d) => d.active === true && d.name === appName)
  .sort((a, b) => b.version - a.version)[0];
if (!latest) {
  fail(`no active beam deployment named "${appName}"`);
}

let url: string | undefined;
try {
  const res = await fetch(`https://app.beam.cloud/api/v1/deployment/${latest.id}/url`, {
    headers: { Authorization: `Bearer ${token()}` },
  });
  if (res.ok) {
    const body = (await res.json()) as { url?: string };
    url = body.url;
  }
} catch {
  fail('beam url lookup failed');
}
if (!url) {
  fail(`beam url lookup returned no url for deployment ${latest.id}`);
}
console.log(url);
