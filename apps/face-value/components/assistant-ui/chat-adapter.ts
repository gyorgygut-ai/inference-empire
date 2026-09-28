"use client";

import { useLocalRuntime } from "@assistant-ui/react";
import { runInference } from "@/app/actions";
import type { ChatModelAdapter, ChatModelRunOptions, ChatModelRunResult, DataMessagePart } from "@assistant-ui/react";
import { useChat } from "./chat-context";
import { useAui } from "@assistant-ui/react";

interface InferenceMessageData {
  imageBase64: string;
  outcomeId: string;
}

function createInferenceAdapter(): ChatModelAdapter {
  return {
    async run(options: ChatModelRunOptions): Promise<ChatModelRunResult> {
      const { messages } = options;
      const lastMessage = messages[messages.length - 1];
      
      if (!lastMessage || lastMessage.role !== "user") {
        return {
          status: { type: "incomplete", reason: "error" },
          content: [{ type: "text", text: "No inference request found" }],
        };
      }

      const inferenceData = lastMessage.content.find(
        (part): part is DataMessagePart => part.type === "data" && (part.data as Record<string, unknown>)?.type === "inference"
      );

      if (!inferenceData || !inferenceData.data) {
        return {
          status: { type: "incomplete", reason: "error" },
          content: [{ type: "text", text: "Invalid inference request" }],
        };
      }

      const data = inferenceData.data as InferenceMessageData;

      try {
        const result = await runInference(data.imageBase64, data.outcomeId);
        
        if ("error" in result) {
          return {
            status: { type: "incomplete", reason: "error" },
            content: [{ type: "text", text: result.error }],
          };
        }

        return {
          status: { type: "complete", reason: "stop" },
          content: [
            {
              type: "image",
              image: result.url,
              filename: `generated-${data.outcomeId}.png`,
            },
          ],
        };
      } catch {
        return {
          status: { type: "incomplete", reason: "error" },
          content: [{ type: "text", text: "Inference failed. Please try again." }],
        };
      }
    },
  };
}

export function useInferenceRuntime() {
  const { selectedOutcomeId, lastImageData } = useChat();
  const aui = useAui();

  const adapter = createInferenceAdapter();

  const runtime = useLocalRuntime(adapter, {});

  const triggerInference = async () => {
    if (!selectedOutcomeId || !lastImageData) return;

    const base64Data = lastImageData.split(",")[1] ?? lastImageData;

    await aui.thread.append({
      role: "user",
      content: [
        {
          type: "data",
          data: {
            type: "inference",
            imageBase64: base64Data,
            outcomeId: selectedOutcomeId,
          } as InferenceMessageData,
        } as DataMessagePart,
      ],
    });
  };

  return { runtime, triggerInference };
}