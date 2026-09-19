import type { ProviderName } from "../task-id"
import type { ProviderAdapter } from "./types"
import { createModalAdapter } from "./modal"
import { createBeamAdapter } from "./beam"
import { createFlashAdapter } from "./flash"

interface SelectorEnv {
  PROVIDER_MODAL_URL: string
  PROVIDER_BEAM_URL: string
  PROVIDER_FLASH_URL: string
}

export function selectProvider(env: SelectorEnv, pinned?: ProviderName): ProviderAdapter {
  if (pinned === "beam") return createBeamAdapter(env.PROVIDER_BEAM_URL)
  if (pinned === "flash") return createFlashAdapter(env.PROVIDER_FLASH_URL)
  return createModalAdapter(env.PROVIDER_MODAL_URL)
}
