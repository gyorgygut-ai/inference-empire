import type { RuntimeConfig } from '../config'
import { strategyBeam } from '../strategies/strategy-beam'
import { strategyModal } from '../strategies/strategy-modal'
import { strategyFlash } from '../strategies/strategy-flash'
import type { Strategy } from '../strategies/strategy'
import type { Provider } from '../task-id'

export function createStrategy(name: Provider, config: RuntimeConfig, fetchImpl: typeof fetch = fetch): Strategy {
  switch (name) {
    case 'beam': return strategyBeam(config, fetchImpl)
    case 'modal': return strategyModal
    case 'flash': return strategyFlash
  }
}
