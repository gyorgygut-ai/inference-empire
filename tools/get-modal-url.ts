#!/usr/bin/env -S npx tsx
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

const workspace = resolve(import.meta.dirname, '..')
const [appName, fnName] = process.argv.slice(2)
const script = [
  'import os, modal',
  'url = modal.Function.from_name(os.environ["MODAL_URL_APP"], os.environ["MODAL_URL_FN"]).get_web_url()',
  'assert url, "no web url"',
  'print(url)',
].join('\n')

console.log(execFileSync('uv', ['run', '--locked', 'python', '-c', script], {
  cwd: workspace, encoding: 'utf8',
  env: { ...process.env, MODAL_URL_APP: appName, MODAL_URL_FN: fnName },
}).trim())
