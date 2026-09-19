export interface CapturedRequest {
  url: string
  init: RequestInit
}

export function createFetchStub(responses: Response[]): typeof fetch & { requests: CapturedRequest[] } {
  const requests: CapturedRequest[] = []
  const impl = (async (url: string | URL | Request, init?: RequestInit): Promise<Response> => {
    requests.push({ url: String(url), init: init ?? {} })
    const next = responses.shift()
    if (next === undefined) throw new Error("fetch stub exhausted")
    return next
  }) as typeof fetch & { requests: CapturedRequest[] }
  impl.requests = requests
  return impl
}

export function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, { status })
}
