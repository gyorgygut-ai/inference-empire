export function encodeTaskId(provider: string, originalTaskId: string): string {
  return btoa(`${provider}:${originalTaskId}`)
}

export function decodeTaskId(encoded: string): { provider: string; originalTaskId: string } {
  const [provider, originalTaskId] = atob(encoded).split(':')
  return { provider, originalTaskId }
}
