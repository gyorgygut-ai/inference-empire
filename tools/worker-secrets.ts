#!/usr/bin/env -S npx tsx
import { resolve } from 'node:path'

const [schemaPath] = process.argv.slice(2)
const { envSchema } = await import(resolve(schemaPath))
console.log(JSON.stringify(envSchema.parse(process.env)))
