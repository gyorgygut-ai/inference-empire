export type ProviderName = "modal" | "beam" | "flash"

interface EncodedTask {
  v: 1
  provider: ProviderName
  id: string
}

export function encodeTaskId(provider: ProviderName, id: string): string {
  const payload: EncodedTask = { v: 1, provider, id }
  return btoa(JSON.stringify(payload)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "")
}

export function decodeTaskId(raw: string): { provider: ProviderName, id: string } | null {
  try {
    const normalized = raw.replaceAll("-", "+").replaceAll("_", "/")
    const parsed: unknown = JSON.parse(atob(normalized))
    if (typeof parsed !== "object" || parsed === null) return null
    const rec = parsed as Record<string, unknown>
    if (rec["v"] !== 1) return null
    if (rec["provider"] !== "modal" && rec["provider"] !== "beam" && rec["provider"] !== "flash") return null
    if (typeof rec["id"] !== "string" || rec["id"].length === 0) return null
    return { provider: rec["provider"], id: rec["id"] }
  } catch {
    return null
  }
}
