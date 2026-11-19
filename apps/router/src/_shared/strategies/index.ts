import type { RuntimeConfig } from '../config'
import { strategyBeam } from './strategy-beam'
import { strategyCloudflare } from './strategy-cloudflare'
import type { Provider, Strategy } from './strategy'

export function createStrategy(provider: Provider, config: RuntimeConfig, fetchImpl: typeof fetch = fetch): Strategy {
  switch (provider) {
    case 'beam': return strategyBeam(config, fetchImpl)
    case 'cloudflare': return strategyCloudflare(config, fetchImpl)
  }
}
