import { describe, test, expect } from "vitest"
import { createModalProvider } from "../src/providers/modal"
import { createFetchStub } from "./stubs/fetch-stub"
import queueIdInput from "./fixtures/providers/modal-queue-id/input.json"
import queueIdExpected from "./fixtures/providers/modal-queue-id/expected.json"
import queueReqInput from "./fixtures/providers/modal-queue-request/input.json"
import queueReqExpected from "./fixtures/providers/modal-queue-request/expected.json"
import doneInput from "./fixtures/providers/modal-status-done/input.json"
import doneExpected from "./fixtures/providers/modal-status-done/expected.json"
import busyInput from "./fixtures/providers/modal-status-busy/input.json"
import busyExpected from "./fixtures/providers/modal-status-busy/expected.json"
import rejectedInput from "./fixtures/providers/modal-status-rejected/input.json"
import rejectedExpected from "./fixtures/providers/modal-status-rejected/expected.json"

function sent(fetchStub: { requests: { url: string, init: RequestInit }[] }): unknown {
  const first = fetchStub.requests[0]
  return {
    url: first.url,
    method: first.init.method,
    auth: (first.init.headers as Record<string, string>)["authorization"],
    body: JSON.parse(first.init.body as string)
  }
}

describe("modal provider", () => {
  test("modal-queue-id", async () => {
    const fetchStub = createFetchStub([{ body: queueIdInput.response }])
    const output = await createModalProvider(queueIdInput.coords, queueIdInput.secrets, fetchStub).queue(queueIdInput.input)
    expect(output).toBe(queueIdExpected)
  })
  test("modal-queue-request", async () => {
    const fetchStub = createFetchStub([{ body: queueReqInput.response }])
    await createModalProvider(queueReqInput.coords, queueReqInput.secrets, fetchStub).queue(queueReqInput.input)
    expect(sent(fetchStub)).toEqual(queueReqExpected)
  })
  test("modal-status-done", async () => {
    const fetchStub = createFetchStub([{ body: doneInput.response }])
    const output = await createModalProvider(doneInput.coords, doneInput.secrets, fetchStub).status(doneInput.id)
    expect(output).toEqual(doneExpected)
  })
  test("modal-status-busy", async () => {
    const fetchStub = createFetchStub([{ body: busyInput.response, status: busyInput.responseStatus }])
    const output = await createModalProvider(busyInput.coords, busyInput.secrets, fetchStub).status(busyInput.id)
    expect(output).toEqual(busyExpected)
  })
  test("modal-status-rejected", async () => {
    const fetchStub = createFetchStub([{ body: rejectedInput.response, status: rejectedInput.responseStatus }])
    const output = await createModalProvider(rejectedInput.coords, rejectedInput.secrets, fetchStub).status(rejectedInput.id)
    expect(output).toEqual(rejectedExpected)
  })
})
