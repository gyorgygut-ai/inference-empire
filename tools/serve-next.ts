#!/usr/bin/env -S npx tsx
import { spawn } from 'node:child_process';
import { env } from 'node:process';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { stripVTControlCharacters } from 'node:util';

const require = createRequire(import.meta.url);

const portArg = process.argv.indexOf('--port');
const port = Number(portArg >= 0 ? process.argv[portArg + 1] : 3000);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error('[serve-next] invalid port');
  process.exit(1);
}

const child = spawn('npx', ['next', 'dev', '--port', String(port)], {
  cwd: join(process.cwd(), 'apps', 'face-value'),
  stdio: ['ignore', 'pipe', 'pipe'],
  env: { ...env, NO_COLOR: '1' },
});

let ready = false;
let outputBuffer = '';
const readyUrlPattern = /Local:\s*(https?:\/\/\S+)/;
const onOutput = (chunk: Buffer, stream: NodeJS.WriteStream) => {
  const text = chunk.toString();
  stream.write(text);
  outputBuffer = `${outputBuffer}${stripVTControlCharacters(text)}`.slice(-8192);
  if (!ready) {
    const completeLines = outputBuffer.slice(0, outputBuffer.lastIndexOf('\n') + 1);
    const readyUrl = readyUrlPattern.exec(completeLines)?.[1];
    if (readyUrl && /Ready in\s/.test(completeLines)) {
      ready = true;
      const { emitReadySignal } = require('@nx/devkit');
      emitReadySignal(readyUrl);
    }
  }
};
child.stdout?.on('data', (chunk: Buffer) => onOutput(chunk, process.stdout));
child.stderr?.on('data', (chunk: Buffer) => onOutput(chunk, process.stderr));
child.on('error', (error) => { console.error(error); process.exit(1); });

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal));
}

child.on('exit', (code) => process.exit(code ?? 1));
