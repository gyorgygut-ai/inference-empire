#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process';

function fail(msg: string): never {
  console.error(`[get-vercel-url] ${msg}`);
  process.exit(1);
}

const args = process.argv.slice(2);
const orgIndex = args.indexOf('--org');
const org = orgIndex === -1 ? undefined : args[orgIndex + 1];
const projectId = args.find((a) => a !== '--org' && a !== org);

const query = `projectId=${encodeURIComponent(projectId)}`;
const apiPath = `/v7/deployments?${query}${org ? `&teamId=${encodeURIComponent(org)}` : ''}`;

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
