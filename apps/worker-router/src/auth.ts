const encoder = new TextEncoder()

export async function verifyToken(providedHeader: string | null, expected: string): Promise<boolean> {
  if (providedHeader === null) return false
  const prefix = "Bearer "
  if (!providedHeader.startsWith(prefix)) return false
  const provided = providedHeader.slice(prefix.length)
  if (provided.length === 0) return false
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(provided)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected))
  ])
  return crypto.subtle.timingSafeEqual(a, b)
}

export function newAuthToken(): string {
  return crypto.randomUUID()
}
