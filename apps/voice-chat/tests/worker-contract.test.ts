import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { once } from "node:events"
import { afterEach, describe, expect, it } from "vitest"
import { createSessionResponse } from "../app/api/voice/session/createSessionResponse"
import { postFastRtcOffer } from "../chat/realtime/fastRtcAdapter"

type CapturedRequest = {
  method: string | undefined
  path: string | undefined
  authorization: string | undefined
  contentType: string | undefined
  body: string
}

const fixturesDir = join(import.meta.dirname, "fixtures")
const readFixture = (name: string) => readFileSync(join(fixturesDir, name), "utf8")
const servers: Array<Server> = []

const startEndpoint = async (response: { status: number; type: string; body: string }) => {
  const requests: Array<CapturedRequest> = []
  const server = createServer((request, result) => captureRequest(request, result, requests, response))
  servers.push(server)
  server.listen(0, "127.0.0.1")
  await once(server, "listening")
  const address = server.address()
  if (!address || typeof address === "string") throw new Error("Local endpoint did not bind")
  return { url: `http://127.0.0.1:${address.port}`, requests }
}

const captureRequest = (
  request: IncomingMessage,
  response: ServerResponse,
  requests: Array<CapturedRequest>,
  result: { status: number; type: string; body: string },
) => {
  let body = ""
  request.on("data", (chunk: Buffer) => { body += chunk.toString() })
  request.on("end", () => {
    requests.push({
      method: request.method,
      path: request.url,
      authorization: request.headers.authorization,
      contentType: request.headers["content-type"],
      body,
    })
    response.writeHead(result.status, { "Content-Type": result.type })
    response.end(result.body)
  })
}

afterEach(async () => {
  await Promise.all(servers.splice(0).map((server) => new Promise<void>((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve())
  })))
})

describe("voice realtime worker HTTP contract", () => {
  it("exchanges the trusted server credential for a client-safe session", async () => {
    const endpoint = await startEndpoint({ status: 200, type: "application/json", body: readFixture("session/worker-response.json") })
    const response = await createSessionResponse(endpoint.url, readFixture("session/server-token.txt"))
    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({
      ...JSON.parse(readFixture("session/expected-response.json")),
      config: { providerOptions: { workerUrl: endpoint.url } },
    })
    expect(endpoint.requests[0]).toMatchObject(JSON.parse(readFixture("session/expected-request.json")))
  })

  it("rejects an invalid session response from the worker", async () => {
    const endpoint = await startEndpoint({ status: 200, type: "application/json", body: readFixture("session/invalid-response.json") })
    const response = await createSessionResponse(endpoint.url, readFixture("session/server-token.txt"))
    expect(response.status).toBe(502)
    expect(await response.json()).toEqual(JSON.parse(readFixture("session/invalid-expected.json")))
  })

  it("posts multipart SDP directly to the worker with the ephemeral bearer token", async () => {
    const endpoint = await startEndpoint({ status: 200, type: "application/sdp", body: readFixture("signaling/answer.sdp") })
    const offer = readFixture("signaling/offer.sdp").trim()
    const answer = await postFastRtcOffer(endpoint.url, readFixture("signaling/token.txt").trim(), offer)
    expect(answer).toBe(readFixture("signaling/answer.sdp"))
    expect(endpoint.requests[0]).toMatchObject(JSON.parse(readFixture("signaling/expected-request.json")))
    expect(endpoint.requests[0]?.contentType).toMatch(/^multipart\/form-data; boundary=/)
    expect(endpoint.requests[0]?.body).toContain(offer)
  })
})
