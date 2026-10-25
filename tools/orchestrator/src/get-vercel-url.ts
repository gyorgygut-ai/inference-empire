#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process';

function fail(msg: string): never {
  console.error(`[get-vercel-url] ${msg}`);
  process.exit(1);
}

const projectId = process.argv[2];
if (!projectId) {
  fail('usage: get-vercel-url.ts <project-id>');
}

const query = `projectId=${encodeURIComponent(projectId)}`;
const apiPath = `/v7/deployments?${query}${process.env.VERCEL_ORG_ID ? `&teamId=${encodeURIComponent(process.env.VERCEL_ORG_ID)}` : ''}`;

let out: string;
try {
  out = execFileSync('vercel', ['api', apiPath, '--raw'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'inherit'],
  });
} catch (error) {
  const code = (error as NodeJS.ErrnoException | undefined)?.code;
  fail(code === 'ENOENT' ? 'vercel CLI not found (npm i -g vercel)' : 'vercel api failed');
}

let url: string | undefined;
try {
  url = (JSON.parse(out) as { deployments?: Array<{ url?: string }> }).deployments?.[0]?.url;
} catch {
  fail('vercel api returned no JSON');
}
if (!url) {
  fail(`no deployments for project ${projectId}`);
}
console.log(url);
