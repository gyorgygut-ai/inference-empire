import { describe, it, expect } from "vitest";
import { forward } from "../src/forward";

const env = {
  RUNPOD_API_KEY: "",
  BEAM_API_KEY: "test-beam-key",
  MODAL_API_KEY: "test-modal-key",
  RUNPOD_ENDPOINT: "",
  BEAM_ENDPOINT: "https://beam.cloud/v1",
  MODAL_ENDPOINT: "https://modal.com/v1",
};

describe("e2e worker flow", () => {
  it("request forwarded to correct provider", () => {
    const req = new Request("https://opencode.ai/v1/chat", { method: "POST" });
    const result = forward(req, "beam", env);
    expect(result.url).toContain("beam.cloud");
    expect(result.url).toContain("/v1/chat");
  });

  it("response passthrough", async () => {
    const mockResponse = new Response("hello from provider", { status: 200 });
    expect(mockResponse.status).toBe(200);
    expect(await mockResponse.text()).toBe("hello from provider");
  });
});
