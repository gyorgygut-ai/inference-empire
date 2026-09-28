import { Provider } from './create-provider'
import { modalProvider } from './provider-modal'
import { beamProvider } from './provider-beam'
import { flashProvider } from './provider-flash'

export default function selectProvider({ provider }: { provider?: string }): Provider {
  const providers: Record<string, Provider> = {
    modal: modalProvider,
    beam: beamProvider,
    flash: flashProvider
  }
  return providers[provider || 'modal'] || modalProvider
}
