import type { ProviderName } from "../task-id"
import type { Provider } from "./types"
import { createModalProvider, type ModalCoordinates, type ModalSecrets } from "./modal"
import { createBeamProvider, type BeamCoordinates, type BeamSecrets } from "./beam"
import { createFlashProvider, type FlashCoordinates, type FlashSecrets } from "./flash"

export interface ContractCoordinates {
  beam: BeamCoordinates | null
  flash: FlashCoordinates | null
  modal: ModalCoordinates | null
}

export interface ProviderSecrets {
  beam: BeamSecrets
  flash: FlashSecrets
  modal: ModalSecrets
}

export function selectProvider(coords: ContractCoordinates, secrets: ProviderSecrets, pinned?: ProviderName, fetchImpl: typeof fetch = fetch): Provider {
  if (pinned === "beam") {
    if (coords.beam === null) throw new Error("beam not configured")
    return createBeamProvider(coords.beam, secrets.beam, fetchImpl)
  }
  if (pinned === "flash") {
    if (coords.flash === null) throw new Error("flash not configured")
    return createFlashProvider(coords.flash, secrets.flash, fetchImpl)
  }
  if (coords.modal === null) throw new Error("modal not configured")
  return createModalProvider(coords.modal, secrets.modal, fetchImpl)
}
