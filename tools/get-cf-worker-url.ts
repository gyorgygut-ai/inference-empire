#!/usr/bin/env -S npx tsx

const workerName = process.argv[2]
const res = await fetch(`https://api.cloudflare.com/client/v4/accounts/${process.env.CLOUDFLARE_ACCOUNT_ID}/workers/subdomain`, {
  headers: { Authorization: `Bearer ${process.env.CLOUDFLARE_API_TOKEN}` },
})
if (!res.ok) throw new Error(await res.text())
const { result } = (await res.json()) as { result: { subdomain: string } }
console.log(`https://${workerName}.${result.subdomain}.workers.dev`)
