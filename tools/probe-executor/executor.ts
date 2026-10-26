import { ExecutorContext } from '@nx/devkit'

export interface ProbeOptions {
  url: string;
  timeout?: number;
}

export default async function probe(
  options: ProbeOptions,
  _context: ExecutorContext
): Promise<{ success: boolean }> {
  const timeout = options.timeout ?? 30000
  const start = Date.now()

  while (Date.now() - start < timeout) {
    try {
      const res = await fetch(options.url, { method: 'HEAD' })
      if (res.ok) {return { success: true }}
    } catch {}
    await new Promise(r => setTimeout(r, 3000))
  }
  throw new Error(`probe failed for ${options.url} within ${timeout}ms`)
}
