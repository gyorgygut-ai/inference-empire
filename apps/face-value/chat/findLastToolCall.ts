"use client";

import { useChatContext } from "@/chat/contexts";
import type { ChatOptions } from "./options";
import type { ToolProps } from "@tanstack/ai-react/ui";

type ToolName = ChatOptions["tools"][number]["name"]
type ToolPart<TName extends ToolName> = Extract<
  ToolProps<ChatOptions>["part"],
  { name: TName }
>

export function findLastToolCall<TName extends ToolName>(
  messages: ReturnType<typeof useChatContext>["messages"],
  name: TName,
) {
  return [...messages]
    .reverse()
    .flatMap(({ parts }) => parts)
    .find((part): part is ToolPart<TName> =>
      part.type === "tool-call" && part.name === name,
    )
}

export function isGenerationLocked(
  messages: ReturnType<typeof useChatContext>["messages"],
) {
  const last = findLastToolCall(messages, "runGenerateImage");
  if (!last || last.type !== "tool-call") {
    return false;
  }

  return last.state === "input-complete" || last.state === "input-streaming"
}
