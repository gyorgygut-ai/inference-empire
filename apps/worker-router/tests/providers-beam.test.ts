import { describe, test, expect } from "vitest"
import { createBeamProvider } from "../src/providers/beam"
import { createFetchStub } from "./stubs/fetch-stub"
import queueIdInput from "./fixtures/providers/beam-queue-id/input.json"
import queueIdExpected from "./fixtures/providers/beam-queue-id/expected.json"
import queueReqInput from "./fixtures/providers/beam-queue-request/input.json"
import queueReqExpected from "./fixtures/providers/beam-queue-request/expected.json"
import doneInput from "./fixtures/providers/beam-status-done/input.json"
import doneExpected from "./fixtures/providers/beam-status-done/expected.json"
import busyInput from "./fixtures/providers/beam-status-busy/input.json"
import busyExpected from "./fixtures/providers/beam-status-busy/expected.json"
import rejectedInput from "./fixtures/providers/beam-status-rejected/input.json"
import rejectedExpected from "./fixtures/providers/beam-status-rejected/expected.json"

function sent(fetchStub: { requests: { url: string, init: RequestInit }[] }): unknown {
  const first = fetchStub.requests[0]
  return {
    url: first.url,
    method: first.init.method,
    auth: (first.init.headers as Record<string, string>)["authorization"],
    body: JSON.parse(first.init.body as string)
  }
}

describe("beam provider", () => {
  test("beam-queue-id", async () => {
    const fetchStub = createFetchStub([{ body: queueIdInput.response }])
    const output = await createBeamProvider(queueIdInput.coords, queueIdInput.secrets, fetchStub).queue(queueIdInput.input)
    expect(output).toBe(queueIdExpected)
  })
  test("beam-queue-request", async () => {
    const fetchStub = createFetchStub([{ body: queueReqInput.response }])
    await createBeamProvider(queueReqInput.coords, queueReqInput.secrets, fetchStub).queue(queueReqInput.input)
    expect(sent(fetchStub)).toEqual(queueReqExpected)
  })
  test("beam-status-done", async () => {
    const fetchStub = createFetchStub([{ body: doneInput.response }])
    const output = await createBeamProvider(doneInput.coords, doneInput.secrets, fetchStub).status(doneInput.id)
    expect(output).toEqual(doneExpected)
  })
  test("beam-status-busy", async () => {
    const fetchStub = createFetchStub([{ body: busyInput.response }])
    const output = await createBeamProvider(busyInput.coords, busyInput.secrets, fetchStub).status(busyInput.id)
    expect(output).toEqual(busyExpected)
  })
  test("beam-status-rejected", async () => {
    const fetchStub = createFetchStub([{ body: rejectedInput.response }])
    const output = await createBeamProvider(rejectedInput.coords, rejectedInput.secrets, fetchStub).status(rejectedInput.id)
    expect(output).toEqual(rejectedExpected)
  })
})
