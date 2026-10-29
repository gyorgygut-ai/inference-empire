#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

const args = process.argv.slice(2)
const dirIndex = args.indexOf('--dir')
const rawDir = dirIndex === -1 ? undefined : args[dirIndex + 1]
const dir = rawDir ? resolve(rawDir) : process.cwd()
const name = args.find((a) => a !== '--dir' && a !== rawDir)

const out = execFileSync('flash', ['undeploy', 'list'], {
  encoding: 'utf8',
  cwd: dir,
  env: { ...process.env, NO_COLOR: '1' },
})

const endpoint = out
  .split('\n')
  .map((line) => line.trim().split(/\s+/).filter(Boolean))
  .find((tokens) => tokens.length >= 3 && tokens[0] === '●' && tokens[1] === name)

if (!endpoint) throw new Error(`no endpoint named "${name}" in flash undeploy list`)
console.log(`https://api.runpod.ai/v2/${endpoint.at(-1)}/infer`)
