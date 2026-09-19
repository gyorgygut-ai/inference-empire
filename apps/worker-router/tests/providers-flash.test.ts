import { describe, test, expect } from "vitest"
import { createFlashProvider } from "../src/providers/flash"
import { createFetchStub } from "./stubs/fetch-stub"
import queueIdInput from "./fixtures/providers/flash-queue-id/input.json"
import queueIdExpected from "./fixtures/providers/flash-queue-id/expected.json"
import queueReqInput from "./fixtures/providers/flash-queue-request/input.json"
import queueReqExpected from "./fixtures/providers/flash-queue-request/expected.json"
import doneInput from "./fixtures/providers/flash-status-done/input.json"
import doneExpected from "./fixtures/providers/flash-status-done/expected.json"
import busyInput from "./fixtures/providers/flash-status-busy/input.json"
import busyExpected from "./fixtures/providers/flash-status-busy/expected.json"
import rejectedInput from "./fixtures/providers/flash-status-rejected/input.json"
import rejectedExpected from "./fixtures/providers/flash-status-rejected/expected.json"

function sent(fetchStub: { requests: { url: string, init: RequestInit }[] }): unknown {
  const first = fetchStub.requests[0]
  return {
    url: first.url,
    method: first.init.method,
    auth: (first.init.headers as Record<string, string>)["authorization"],
    body: JSON.parse(first.init.body as string)
  }
}

describe("flash provider", () => {
  test("flash-queue-id", async () => {
    const fetchStub = createFetchStub([{ body: queueIdInput.response }])
    const output = await createFlashProvider(queueIdInput.coords, queueIdInput.secrets, fetchStub).queue(queueIdInput.input)
    expect(output).toBe(queueIdExpected)
  })
  test("flash-queue-request", async () => {
    const fetchStub = createFetchStub([{ body: queueReqInput.response }])
    await createFlashProvider(queueReqInput.coords, queueReqInput.secrets, fetchStub).queue(queueReqInput.input)
    expect(sent(fetchStub)).toEqual(queueReqExpected)
  })
  test("flash-status-done", async () => {
    const fetchStub = createFetchStub([{ body: doneInput.response }])
    const output = await createFlashProvider(doneInput.coords, doneInput.secrets, fetchStub).status(doneInput.id)
    expect(output).toEqual(doneExpected)
  })
  test("flash-status-busy", async () => {
    const fetchStub = createFetchStub([{ body: busyInput.response }])
    const output = await createFlashProvider(busyInput.coords, busyInput.secrets, fetchStub).status(busyInput.id)
    expect(output).toEqual(busyExpected)
  })
  test("flash-status-rejected", async () => {
    const fetchStub = createFetchStub([{ body: rejectedInput.response }])
    const output = await createFlashProvider(rejectedInput.coords, rejectedInput.secrets, fetchStub).status(rejectedInput.id)
    expect(output).toEqual(rejectedExpected)
  })
})
