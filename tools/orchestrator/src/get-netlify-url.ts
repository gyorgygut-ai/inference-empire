#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process'

function fail(msg: string): never {
  console.error(`[get-netlify-url] ${msg}`)
  process.exit(1)
}

const siteId = process.argv[2]

let out: string
try {
  out = execFileSync('netlify', ['api', 'getSite', '--data', JSON.stringify({ site_id: siteId })], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'inherit'],
  })
} catch (error) {
  const code = (error as NodeJS.ErrnoException | undefined)?.code
  fail(code === 'ENOENT' ? 'netlify CLI not found (npm i -g netlify-cli)' : 'netlify api getSite failed')
}

let url: string | undefined
try {
  url = (JSON.parse(out) as { url?: string }).url
} catch {
  fail('netlify api getSite returned no JSON')
}
if (!url) {
  fail('netlify api getSite returned no url')
}
console.log(url)
