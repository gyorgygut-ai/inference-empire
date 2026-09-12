import { describe, it, expect } from "vitest";
import { forward } from "../src/forward";

describe("forward", () => {
  it("rewrites host to provider endpoint", () => {
    const env = {
      RUNPOD_API_KEY: "rkey",
      BEAM_API_KEY: "bkey",
      MODAL_API_KEY: "mkey",
      RUNPOD_ENDPOINT: "https://runpod.io/v1",
      BEAM_ENDPOINT: "https://beam.cloud/v1",
      MODAL_ENDPOINT: "https://modal.com/v1",
    };

    const req = new Request("https://opencode.ai/v1/chat", { method: "POST" });
    const result = forward(req, "runpod", env);

    expect(result.url).toContain("runpod.io");
    expect(result.url).toContain("/v1/chat");
    expect(result.method).toBe("POST");
  });

  it("preserves path and method", () => {
    const env = {
      RUNPOD_API_KEY: "",
      BEAM_API_KEY: "",
      MODAL_API_KEY: "",
      RUNPOD_ENDPOINT: "https://runpod.io",
      BEAM_ENDPOINT: "https://beam.cloud",
      MODAL_ENDPOINT: "https://modal.com",
    };

    const req = new Request("https://anything.com/some/deep/path?q=1", { method: "PUT" });
    const result = forward(req, "modal", env);

    expect(result.url).toContain("modal.com");
    expect(result.url).toContain("/some/deep/path?q=1");
    expect(result.method).toBe("PUT");
  });
});
