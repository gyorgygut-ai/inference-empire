"use client";

import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { ChatProvider, useChat } from "./chat-context";
import { Thread } from "./elements/thread.aui";
import { useInferenceRuntime } from "./chat-adapter";
import type { Outcome } from "@/outcomes";

interface ChatClientProps {
  outcomes: Outcome[];
}

function ChatClientInner({ outcomes }: ChatClientProps) {
  const { runtime } = useInferenceRuntime();

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <Thread outcomes={outcomes} />
    </AssistantRuntimeProvider>
  );
}

export function ChatClient({ outcomes }: ChatClientProps) {
  return (
    <ChatProvider>
      <ChatClientInner outcomes={outcomes} />
    </ChatProvider>
  );
}