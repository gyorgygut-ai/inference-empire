import { describe, it, expect } from "vitest"
import { Flux2Klein9BInput, Flux2Klein9BOutput } from "@/app/inference-api/schema"

describe("Flux2Klein9BOutput", () => {
  it("artifact is { presigned_url: string }", () => {
    const output: Flux2Klein9BOutput = {
      artifact: { presigned_url: "https://example.com/image.png" },
    }
    expect(output.artifact.presigned_url).toBe("https://example.com/image.png")
  })

  it("does not allow artifact as string", () => {
    const bad = {
      // @ts-expect-error - artifact must be object with presigned_url
      artifact: "https://example.com/image.png",
    }
    expect(bad.artifact).toBe("https://example.com/image.png")
  })
})

describe("Flux2Klein9BInput", () => {
  it("accepts input_image as string", () => {
    const input: Flux2Klein9BInput = {
      prompt: "test",
      input_image: "base64data",
    }
    expect(input.input_image).toBe("base64data")
  })

  it("accepts optional width and height", () => {
    const input: Flux2Klein9BInput = {
      prompt: "test",
      width: 1024,
      height: 1024,
    }
    expect(input.width).toBe(1024)
    expect(input.height).toBe(1024)
  })
})
