import { createHash } from "crypto"

const inferenceCache = new Map<string, { imageUrl: string }>()

export function cacheKeyForImage(image: Buffer, outcomeId: string): string {
  return `${createHash("sha256").update(image).digest("hex")}:${outcomeId}`
}

export function getCachedImage(key: string): { imageUrl: string } | undefined {
  return inferenceCache.get(key)
}

export function setCachedImage(key: string, value: { imageUrl: string }): void {
  inferenceCache.set(key, value)
}

export function clearInferenceCache(): void {
  inferenceCache.clear()
}
