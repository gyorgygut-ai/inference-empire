#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

function fail(msg: string): never {
  console.error(`[get-flash-url] ${msg}`)
  process.exit(1)
}

const args = process.argv.slice(2)
const dirIndex = args.indexOf('--dir')
const rawDir = dirIndex === -1 ? undefined : args[dirIndex + 1]
const dir = rawDir ? resolve(rawDir) : process.cwd()
const name = args.find((a) => a !== '--dir' && a !== rawDir)

let out: string
try {
  out = execFileSync('flash', ['undeploy', 'list'], {
    encoding: 'utf8',
    cwd: dir,
    stdio: ['ignore', 'pipe', 'inherit'],
    env: { ...process.env, NO_COLOR: '1' },
  })
} catch {
  fail(`flash undeploy list failed (dir: ${dir})`)
}

const ansiPattern = new RegExp(`${String.fromCharCode(27)}\\[[0-9;]*m`, 'g')
const stripAnsi = (s: string): string => s.replace(ansiPattern, '')
let endpointId: string | undefined
for (const line of stripAnsi(out).split('\n')) {
  // rendered line: "● <name> <endpoint-id>"
  const tokens = line.trim().split(/\s+/).filter(Boolean)
  if (tokens.length >= 3 && tokens[0] === '●' && tokens[1] === name) {
    endpointId = tokens[tokens.length - 1]
  }
}
if (!endpointId) {
  fail(`no endpoint named "${name}" in flash undeploy list (dir: ${dir})`)
}
console.log(`https://api.runpod.ai/v2/${endpointId}/infer`)
