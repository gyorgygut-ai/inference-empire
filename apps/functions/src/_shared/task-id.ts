import { z } from 'zod'

export const providerSchema = z.enum(['beam', 'modal', 'flash'])
export type Provider = z.infer<typeof providerSchema>

function encodeBase64(text: string): string {
  let binary = ''
  for (const byte of new TextEncoder().encode(text)) {binary += String.fromCharCode(byte)}
  return btoa(binary)
}

function decodeBase64(encoded: string): string {
  const binary = atob(encoded)
  if (btoa(binary) !== encoded) {throw new Error('Invalid task id encoding')}
  return new TextDecoder('utf-8', { fatal: true }).decode(Uint8Array.from(binary, char => char.charCodeAt(0)))
}

export function encodeTaskId(provider: Provider, originalTaskId: string): string {
  if (!originalTaskId) {throw new Error('Empty task id')}
  return encodeBase64(`${provider}:${originalTaskId}`)
}

export function decodeTaskId(encoded: string) {
  const decoded = decodeBase64(encoded)
  const separator = decoded.indexOf(':')
  if (separator < 1 || !decoded.slice(separator + 1)) {throw new Error('Invalid task id format')}
  return { provider: providerSchema.parse(decoded.slice(0, separator)), originalTaskId: decoded.slice(separator + 1) }
}
