export interface CapturedRequest {
  url: string
  init: RequestInit
}

export interface StubbedResponse {
  body?: unknown
  status?: number
}

export function createFetchStub(responses: StubbedResponse[]): typeof fetch & { requests: CapturedRequest[] } {
  const requests: CapturedRequest[] = []
  const impl: typeof fetch & { requests: CapturedRequest[] } = async (url: string | URL | Request, init?: RequestInit): Promise<Response> => {
    requests.push({ url: String(url), init: init ?? {} })
    const next = responses.shift()
    if (next === undefined) {
      throw new Error("fetch stub exhausted")
    }
    return Response.json(next.body, { status: next.status ?? 200 })
  }
  impl.requests = requests
  return impl
}
