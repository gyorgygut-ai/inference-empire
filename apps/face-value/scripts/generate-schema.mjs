import { writeFile } from "node:fs/promises"
import { resolve } from "node:path"
import { compile } from "json-schema-to-typescript"

const CONTRACT_URL =
  "https://raw.githubusercontent.com/gyorgygutai/runpod-flash-workers/main/contracts/flux2_klein9b.json"

const contract = await fetch(CONTRACT_URL).then((r) => r.json())

const input = await compile(contract.input, contract.input.title, {
  bannerComment: "",
})
const output = await compile(contract.output, contract.output.title, {
  bannerComment: "",
})

const generated = `/* This file was auto-generated from the inference contract. Do not edit directly. */

${input.trim()}

${output.trim()}
`

const outPath = resolve(process.cwd(), "app/inference-api/schema.ts")
await writeFile(outPath, generated)
