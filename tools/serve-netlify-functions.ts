#!/usr/bin/env -S npx tsx
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { env as processEnv } from 'node:process';
import { createRequire } from 'node:module';
import { stripVTControlCharacters } from 'node:util';

const require = createRequire(import.meta.url);

const functionsRoot = join(process.cwd(), 'apps', 'functions');
const netlifyToml = readFileSync(join(functionsRoot, 'netlify.toml'), 'utf8');
const devTable = /\[dev\]([\s\S]*?)(?=\n\[|$)/.exec(netlifyToml)?.[1] ?? '';
const portArg = process.argv.indexOf('--port');
const port = Number(portArg >= 0 ? process.argv[portArg + 1] : /port\s*=\s*(\d+)/.exec(devTable)?.[1]);

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error('[serve-netlify-functions] invalid port');
  process.exit(1);
}

const child = spawn('npx', ['netlify', 'dev', '--port', String(port)], {
  cwd: functionsRoot,
  stdio: ['ignore', 'pipe', 'pipe'],
  env: { ...processEnv, NO_COLOR: '1' },
});

let ready = false;
let outputBuffer = '';
const readyUrlPattern = /Local dev server ready:\s*(https?:\/\/\S+)/;
const onOutput = (chunk: Buffer, stream: NodeJS.WriteStream) => {
  const text = chunk.toString();
  stream.write(text);
  outputBuffer = `${outputBuffer}${stripVTControlCharacters(text)}`.slice(-8192);
  if (!ready) {
    const completeLines = outputBuffer.slice(0, outputBuffer.lastIndexOf('\n') + 1);
    const readyUrl = readyUrlPattern.exec(completeLines)?.[1];
    if (readyUrl) {
      ready = true;
      const { emitReadySignal } = require('@nx/devkit');
      emitReadySignal(readyUrl);
    }
  }
};
child.stdout?.on('data', (chunk: Buffer) => onOutput(chunk, process.stdout));
child.stderr?.on('data', (chunk: Buffer) => onOutput(chunk, process.stderr));
child.on('error', (error) => { console.error(error); process.exit(1); });

for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => child.kill(sig));
}

child.on('exit', (code) => process.exit(code ?? 1));
