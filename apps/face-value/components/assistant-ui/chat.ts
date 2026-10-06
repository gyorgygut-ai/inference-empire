import { CreateAppendMessage } from "@assistant-ui/react";

export enum ChatPhase {
  PROMPT_FOR_OUTCOME = "PROMPT_FOR_OUTCOME",
  PROMPT_FOR_REFERENCE = "PROMPT_FOR_REFERENCE",
  INFERENCE_BUSY = "INFERENCE_BUSY",
  INFERENCE_REJECTED = "INFERENCE_REJECTED",
  INFERENCE_FULFILLED = "INFERENCE_FULFILLED",
  REQUEST_INFERENCE = "request-inference",
}

export const createMessage = (type: ChatPhase, text = "") =>
  ({
    role: "assistant",
    metadata: { custom: { type } },
    content: [{ type: "text", text }],
  }) satisfies CreateAppendMessage;
