"use client"

import { AssistantRuntimeProvider, useLocalRuntime, type ChatModelAdapter } from "@assistant-ui/react"
import { ReactNode } from "react"

const Adapter: ChatModelAdapter = {
  async run() {
    return { content: [{ type: "text", text: "" }] }
  }
}

export function RuntimeProvider({ children }: { children: ReactNode }) {
  const runtime = useLocalRuntime(Adapter)
  return <AssistantRuntimeProvider runtime={runtime}>{children}</AssistantRuntimeProvider>
}
