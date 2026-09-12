import { describe, it, expect } from "vitest";
import { route } from "../src/handler-chain";
import { buildState } from "./mocks/state";

const req = new Request("https://example.com/v1/chat");

describe("handler chain", () => {
  it("free quota wins", () => {
    const state = buildState({
      modal: { freeQuota: 10 },
      beam: { balance: 50 },
    });
    expect(route(req, state)).toBe("modal");
  });

  it("balance fallback when no free quota", () => {
    const state = buildState({
      beam: { balance: 50 },
      modal: { balance: 20 },
    });
    expect(route(req, state)).toBe("beam");
  });

  it("rate limit skip", () => {
    const state = buildState({
      beam: { rateLimitRemaining: 0 },
      modal: { rateLimitRemaining: 10 },
    });
    expect(route(req, state)).toBe("modal");
  });

  it("availability skip", () => {
    const state = buildState({
      beam: { available: false, rateLimitRemaining: 0 },
      modal: { available: true, rateLimitRemaining: 0 },
    });
    expect(route(req, state)).toBe("modal");
  });

  it("fallback when nothing else matches", () => {
    const state = buildState({
      modal: { rateLimitRemaining: 0, balance: 0, freeQuota: 0, available: false },
      beam: { rateLimitRemaining: 0, balance: 0, freeQuota: 0, available: false },
    });
    expect(route(req, state)).toBe("beam");
  });
});
