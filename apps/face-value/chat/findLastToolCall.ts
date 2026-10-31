"use client";

import { useChatContext } from "@/chat/client";
import type { ChatOptions } from "./options";

export function findLastToolCall(
  messages: ReturnType<typeof useChatContext>["messages"],
  name: ChatOptions["tools"][number]["name"],
) {
  return [...messages]
    .reverse()
    .flatMap(({ parts }) => parts)
    .find((part) => part.type === "tool-call" && part.name === name);
}

export function isGenerationLocked(
  messages: ReturnType<typeof useChatContext>["messages"],
) {
  const last = findLastToolCall(messages, "runGenerateImage");
  if (!last || last.type !== "tool-call") {
    return false;
  }

  return last.state !== "approval-requested";
}
