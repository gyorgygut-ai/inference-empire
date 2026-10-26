#!/usr/bin/env -S npx tsx
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { jsonSchemaToZod } from 'x-to-zod';

function generate(schemaPath: string, outPath: string) {
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
}

const [schemaPath, outPath] = process.argv.slice(2);
if (schemaPath === '--all') {
  const root = fileURLToPath(new URL('./schemas/', import.meta.url));
  for (const entry of readdirSync(root, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const input = join(root, entry.name, 'schema.json');
    if (entry.isDirectory() && existsSync(input)) generate(input, join(root, entry.name, 'schema.ts'));
  }
} else {
  if (!schemaPath || !outPath) throw new Error('usage: generate-zod-from-json.ts --all | <schema-json> <out-ts>');
  generate(schemaPath, outPath);
}
