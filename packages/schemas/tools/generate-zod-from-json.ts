#!/usr/bin/env -S npx tsx
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { parseArgs } from 'node:util'
import { jsonSchemaToZod } from 'x-to-zod'

function generate(schemaPath: string, outPath: string) {
  const schema = JSON.parse(readFileSync(schemaPath, 'utf8'))
  const code = jsonSchemaToZod(schema, {
    name: 'api',
    module: 'esm',
    type: true,
    zodVersion: 'v4',
  })

  mkdirSync(dirname(outPath), { recursive: true })
  writeFileSync(outPath, `${code.trimEnd()}\n`)
  console.log(outPath)
}

const { values } = parseArgs({
  options: {
    source: { type: 'string' },
    out: { type: 'string' },
  },
  allowPositionals: false,
  strict: true,
})

if (!values.source || !values.out) {
  throw new Error('usage: generate-zod-from-json.ts --source <schema-json> --out <output-ts>')
}

generate(values.source, values.out)
