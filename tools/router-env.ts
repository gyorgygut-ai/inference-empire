#!/usr/bin/env -S npx tsx
import { mkdirSync, writeFileSync } from 'node:fs';
import { generateAuthToken } from './generate-auth-token';
import { routerPortsSchema } from '../apps/router/env.schema';

const [model, environment] = process.argv.slice(2);
if ((model !== 'flux2' && model !== 'krea2') || (environment !== 'dev' && environment !== 'deploy')) {
  console.error('usage: router-env.ts <flux2|krea2> <dev|deploy>');
  process.exit(1);
}

const ports = routerPortsSchema.parse(process.env);
const port = model === 'flux2' ? ports.FLUX2_ROUTER_PORT : ports.KREA2_ROUTER_PORT;

const dir = `dist/router-${model}/${environment}`;
mkdirSync(dir, { recursive: true });

const write = (name: string, value: string): void => {
  writeFileSync(`${dir}/${name}`, `${value}\n`);
};

write('SECRET_AUTH_TOKEN', generateAuthToken());

if (environment === 'dev') {
  write('PORT', String(port));
  write('ROUTER_URL', `http://localhost:${port}`);
}

console.error(`[router-env] wrote ${dir}`);
