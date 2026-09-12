import runpod from "runpod-sdk"
import { EndpointCompletedOutput } from "runpod-sdk/src"
import type { Flux2Klein9BInput, Flux2Klein9BOutput } from "./schema"

export type RequestPayload = Flux2Klein9BInput

export type ResponsePayload = Flux2Klein9BOutput

const { INFERENCE_TOKEN, INFERENCE_ENDPOINT_ID } = process.env

const client = runpod(INFERENCE_TOKEN)
const inferenceEndpoint = client.endpoint(INFERENCE_ENDPOINT_ID)

const RUNPOD_TIMEOUT = 60000 * 5
const PING_TIMEOUT = 1000

export async function pingInference(): Promise<boolean> {
  try {
    const check = await inferenceEndpoint!.health(PING_TIMEOUT)
    return typeof check === "object" && check !== null && "workers" in check
  } catch {
    return false
  }
}

export function runInferenceWithPolling(input: RequestPayload) {
  return inferenceEndpoint!.runSync({ input }, RUNPOD_TIMEOUT) as Promise<
    EndpointCompletedOutput & { output: ResponsePayload }
  >
}
