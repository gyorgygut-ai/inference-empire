import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { AssistantRuntimeProvider, useLocalRuntime, AuiConfig, Suggestions, type ChatModelAdapter } from "@assistant-ui/react"
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

function createWrapper(outcomes: { id: string, title: string }[]) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    const runtime = useLocalRuntime(mockAdapter, {})
    const config = AuiConfig({
      suggestions: Suggestions(outcomes.map((o) => ({ title: o.title, label: o.title, prompt: o.title }))),
    })
    return (
      <ChatProvider>
        <AssistantRuntimeProvider runtime={runtime} config={config}>{children}</AssistantRuntimeProvider>
      </ChatProvider>
    )
  }
}

function renderThread(outcomes: { id: string, title: string }[]) {
  return render(<Thread components={{ Welcome: OutcomeWelcome }} />, { wrapper: createWrapper(outcomes) })
}

describe("Thread", () => {
  it("renders outcome suggestions when thread is empty", () => {
    const outcomes = [
      { id: "outcome-1", title: "Oil Painting" },
      { id: "outcome-2", title: "Watercolor" },
    ]
    renderThread(outcomes)
    expect(screen.getByText("Oil Painting")).toBeInTheDocument()
    expect(screen.getByText("Watercolor")).toBeInTheDocument()
  })

  it("clicking a suggestion selects the outcome", async () => {
    const user = userEvent.setup()
    const outcomes = [{ id: "outcome-1", title: "Oil Painting" }]
    renderThread(outcomes)
    await user.click(screen.getByText("Oil Painting"))
    expect(screen.getByRole("button", { pressed: true })).toHaveTextContent("Oil Painting")
  })

  it("renders no image before any generation", () => {
    const outcomes: { id: string, title: string }[] = []
    renderThread(outcomes)
    expect(screen.queryByRole("img", { name: /generated|image content/i })).not.toBeInTheDocument()
  })
})
