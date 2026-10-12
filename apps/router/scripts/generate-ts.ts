import { readFileSync, writeFileSync } from 'node:fs';
import { compile } from 'json-schema-to-typescript';

const [inPath, outPath] = process.argv.slice(2);
if (!inPath || !outPath) throw new Error('usage: generate-ts.ts <in.json> <out.ts>');

const doc = JSON.parse(readFileSync(inPath, 'utf8')) as {
  schemas: Record<string, object>;
};

const names = Object.keys(doc.schemas).sort();
const parts: string[] = [];
for (const name of names) {
  parts.push(await compile(doc.schemas[name], name, { bannerComment: '' }));
}

writeFileSync(outPath, parts.join('\n') + '\n');
console.log(`[generate-ts] wrote ${outPath}`);
