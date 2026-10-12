import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

const root = process.cwd();
const flavor = process.argv[2];
if (!flavor) {
  console.error('usage: generate-api.ts <flavor>');
  process.exit(1);
}
const workerDir = flavor;
const name = flavor.replace(/-/g, '_');

const inference = JSON.parse(
  readFileSync(join(root, 'packages/contracts', workerDir, 'inference.json'), 'utf8')
) as { input: unknown; output: unknown };
const api = JSON.parse(readFileSync(join(root, 'packages/contracts/api-task-queue.json'), 'utf8')) as {
  title: string;
  endpoints: unknown;
  inferRequest: { properties: Record<string, unknown> };
  inferResponse: unknown;
  inquireResponse: { properties: Record<string, unknown> };
};

const out = {
  title: `${api.title}(${flavor})`,
  endpoints: api.endpoints,
  schemas: {
    InferRequest: {
      ...api.inferRequest,
      properties: { ...api.inferRequest.properties, input: inference.input },
    },
    InferResponse: api.inferResponse,
    InquireResponse: {
      ...api.inquireResponse,
      properties: { ...api.inquireResponse.properties, output: inference.output },
    },
  },
};

const outPath = join(root, 'apps/router/dist', `${name}_api.json`);
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, `${JSON.stringify(out, null, 2)}\n`);
console.log(`[generate-api] wrote ${outPath}`);
