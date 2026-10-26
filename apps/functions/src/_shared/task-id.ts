import { z } from 'zod'

export const providerSchema = z.enum(['beam', 'modal', 'flash'])
export type Provider = z.infer<typeof providerSchema>

export function encodeTaskId(provider: Provider, originalTaskId: string): string {
  if (!originalTaskId) {throw new Error('Empty task id')}
  return Buffer.from(`${provider}:${originalTaskId}`, 'utf8').toString('base64')
}

export function decodeTaskId(encoded: string) {
  const bytes = Buffer.from(encoded, 'base64')
  if (bytes.toString('base64') !== encoded) {throw new Error('Invalid task id encoding')}
  const decoded = bytes.toString('utf8')
  const separator = decoded.indexOf(':')
  if (separator < 1 || !decoded.slice(separator + 1)) {throw new Error('Invalid task id format')}
  if (Buffer.from(decoded, 'utf8').compare(bytes) !== 0) {throw new Error('Invalid task id encoding')}
  return { provider: providerSchema.parse(decoded.slice(0, separator)), originalTaskId: decoded.slice(separator + 1) }
}
