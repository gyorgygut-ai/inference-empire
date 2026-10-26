#!/usr/bin/env -S npx tsx
import { randomBytes } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { parse } from 'dotenv'
import { z } from 'zod'

const [envFile, key] = process.argv.slice(2)
if (!envFile || !key) {
  throw new Error('usage: resolve-auth-token.ts <env-file> <key>')
}

if (existsSync(envFile)) {
  const current = parse(readFileSync(envFile, 'utf8'))[key]
  if (current !== undefined) {
    console.log(z.string().min(32).parse(current))
    process.exit(0)
  }
}

console.log(randomBytes(32).toString('base64url'))
