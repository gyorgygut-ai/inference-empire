"use client";

import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from "@assistant-ui/react";
import { SimpleImageAttachmentAdapter } from "@assistant-ui/react";
import type { ReactNode } from "react";

const Adapter: ChatModelAdapter = {
  async run() {
    return { content: [{ type: "text", text: "" }] };
  },
};

const attachmentAdapter = new SimpleImageAttachmentAdapter();

export const RuntimeProvider = ({
  childrenFn,
  suggestions,
}: {
  childrenFn: () => ReactNode;
  suggestions: { id: string; title: string }[];
}) => {
  const runtime = useLocalRuntime(Adapter, {
    adapters: {
      attachments: attachmentAdapter,
      suggestion: {
        generate: async () =>
          suggestions.map((s) => ({ title: s.title, prompt: s.id })),
      },
    },
  });
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ChildrenFnWrapper fn={childrenFn} />
    </AssistantRuntimeProvider>
  );
};

function ChildrenFnWrapper({ fn }: { fn: () => ReactNode }) {
  return fn();
}
