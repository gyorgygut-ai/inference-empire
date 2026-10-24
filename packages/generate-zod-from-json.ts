#!/usr/bin/env -S npx tsx
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { jsonSchemaToZod } from 'x-to-zod';

const [schemaPath, outPath] = process.argv.slice(2);
if (!schemaPath || !outPath) {
  throw new Error('usage: generate-zod-from-json.ts <schema-json> <out-ts>');
}

const schema = JSON.parse(readFileSync(schemaPath, 'utf8'));
const code = jsonSchemaToZod(schema, {
  name: 'api',
  module: 'esm',
  type: true,
  zodVersion: 'v4',
});

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, `${code.trimEnd()}\n`);
console.log(outPath);

process.exit(0); // Explicitly exit successfully