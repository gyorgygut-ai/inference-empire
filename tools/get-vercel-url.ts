#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process'

const args = process.argv.slice(2)
const orgIndex = args.indexOf('--org')
const org = orgIndex === -1 ? undefined : args[orgIndex + 1]
const projectId = args.find((a) => a !== '--org' && a !== org)

const query = `projectId=${encodeURIComponent(projectId)}`
const apiPath = `/v7/deployments?${query}${org ? `&teamId=${encodeURIComponent(org)}` : ''}`

const { deployments } = JSON.parse(execFileSync('vercel', ['api', apiPath, '--raw'], { encoding: 'utf8' })) as {
  deployments: Array<{ url: string }>
}
console.log(`https://${deployments[0].url}`)
