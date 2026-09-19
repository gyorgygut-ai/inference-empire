import { describe, test, expect } from "vitest"
import { createModalProvider } from "../src/providers/modal"
import { createBeamProvider } from "../src/providers/beam"
import { createFlashProvider } from "../src/providers/flash"
import { createFetchStub } from "./stubs/fetch-stub"
import modalInput from "./fixtures/providers/interface-modal/input.json"
import modalExpected from "./fixtures/providers/interface-modal/expected.json"
import beamInput from "./fixtures/providers/interface-beam/input.json"
import beamExpected from "./fixtures/providers/interface-beam/expected.json"
import flashInput from "./fixtures/providers/interface-flash/input.json"
import flashExpected from "./fixtures/providers/interface-flash/expected.json"

describe("provider interface", () => {
  test("interface-modal", async () => {
    const provider = createModalProvider(modalInput.coords, modalInput.secrets, createFetchStub([{ body: modalInput.response }]))
    const output = { name: provider.name, hasQueue: typeof provider.queue, hasStatus: typeof provider.status }
    expect(output).toEqual(modalExpected)
  })
  test("interface-beam", async () => {
    const provider = createBeamProvider(beamInput.coords, beamInput.secrets, createFetchStub([{ body: beamInput.response }]))
    const output = { name: provider.name, hasQueue: typeof provider.queue, hasStatus: typeof provider.status }
    expect(output).toEqual(beamExpected)
  })
  test("interface-flash", async () => {
    const provider = createFlashProvider(flashInput.coords, flashInput.secrets, createFetchStub([{ body: flashInput.response }]))
    const output = { name: provider.name, hasQueue: typeof provider.queue, hasStatus: typeof provider.status }
    expect(output).toEqual(flashExpected)
  })
})
