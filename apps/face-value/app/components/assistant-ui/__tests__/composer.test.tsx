import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { AssistantRuntimeProvider, useLocalRuntime, type ChatModelAdapter } from "@assistant-ui/react"
import React from "react"
import { Thread } from "@/components/assistant-ui/elements/thread.aui"
import OutcomeWelcome from "@/app/components/assistant-ui/outcome-welcome"
import { ChatProvider } from "@/app/components/assistant-ui/chat-context"

const mockAdapter: ChatModelAdapter = {
  async run() {
    return {
      content: [{ type: "text", text: "Runtime bridge pending." }],
    }
  },
}

function createWrapper() {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    const runtime = useLocalRuntime(mockAdapter, {})
    return (
      <ChatProvider>
        <AssistantRuntimeProvider runtime={runtime}>{children}</AssistantRuntimeProvider>
      </ChatProvider>
    )
  }
}

function renderComposer() {
  return render(<Thread components={{ Welcome: OutcomeWelcome }} />, { wrapper: createWrapper() })
}

describe("Composer", () => {
  it("send button disabled until outcome selected and image attached", () => {
    renderComposer()
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled()
  })

  it("add attachment disabled until outcome selected", () => {
    renderComposer()
    expect(screen.getByRole("button", { name: "Add Attachment" })).toBeDisabled()
  })

  it("prompts outcome selection before attachment", () => {
    renderComposer()
    expect(screen.getByPlaceholderText("Select an outcome above...")).toBeInTheDocument()
  })
})
