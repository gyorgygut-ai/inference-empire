"use client";

import { useEffect } from "react";
import { AssistantRuntimeProvider, useAui } from "@assistant-ui/react";
import { ChatProvider, useChat } from "./chat-context";
import { Thread } from "./elements/thread.aui";
import { useInferenceRuntime } from "./chat-adapter";
import { vocabulary } from "@/app/vocabulary";
import type { Outcome } from "@/outcomes";

interface ChatClientProps {
  outcomes: Outcome[];
}

function ChatClientInner({ outcomes }: ChatClientProps) {
  const { runtime } = useInferenceRuntime();
  const { setHasAttachment, setLastImageData, setSelectedOutcomeId } = useChat();
  const aui = useAui();

  useEffect(() => {
    setSelectedOutcomeId(null);
    setHasAttachment(false);
    setLastImageData(null);
    aui.thread.append({
      role: "assistant",
      content: [{ type: "text", text: vocabulary.steps.outcome.message }],
    });
  }, []);

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