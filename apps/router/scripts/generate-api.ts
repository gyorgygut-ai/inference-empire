import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';

const [queuePath, inferencePath, outPath] = process.argv.slice(2);
if (!queuePath || !inferencePath || !outPath) throw new Error('usage: generate-api.ts <queue.json> <inference.json> <out.json>');

const api = JSON.parse(readFileSync(queuePath, 'utf8'));
const inference = JSON.parse(readFileSync(inferencePath, 'utf8'));

const out = {
  title: api.title,
  endpoints: api.endpoints,
  schemas: {
    AddToQueueRequest: { ...api.addToQueueRequest, properties: { ...api.addToQueueRequest.properties, input: inference.input } },
    AddToQueueResponse: api.addToQueueResponse,
    SupResponse: { ...api.supResponse, properties: { ...api.supResponse.properties, output: inference.output } },
  },
};

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n');
console.log(`[generate-api] wrote ${outPath}`);
