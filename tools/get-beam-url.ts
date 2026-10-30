#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process'
import { stripVTControlCharacters } from 'node:util'

const appName = process.argv[2]
const deployments = JSON.parse(stripVTControlCharacters(execFileSync('beam', ['deployment', 'list', '--format', 'json', '--limit', '100'], {
  encoding: 'utf8',
  env: { ...process.env, NO_COLOR: '1', FORCE_COLOR: '0' },
}))) as Array<{ id: string; name: string; active: boolean; version: number }>

const latest = deployments
  .filter((d) => d.active === true && d.name === appName)
  .sort((a, b) => b.version - a.version)[0]

const res = await fetch(`https://app.beam.cloud/api/v1/deployment/${latest.id}/url`, {
  headers: { Authorization: `Bearer ${process.env.SECRET_BEAM_TOKEN}` },
})
if (!res.ok) throw new Error(await res.text())
const { url } = (await res.json()) as { url: string }
console.log(url)
