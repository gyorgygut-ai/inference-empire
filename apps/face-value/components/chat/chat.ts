export enum ChatPhase {
  PROMPT_FOR_OUTCOME = "PROMPT_FOR_OUTCOME",
  PROMPT_FOR_REFERENCE = "PROMPT_FOR_REFERENCE",
  INFERENCE_BUSY = "INFERENCE_BUSY",
  INFERENCE_REJECTED = "INFERENCE_REJECTED",
  INFERENCE_FULFILLED = "INFERENCE_FULFILLED",
  REQUEST_INFERENCE = "request-inference",
}

export interface AppMessageMetadata {
  custom?: {
    type?: ChatPhase;
    outcomeId?: string;
    artifactUrl?: string;
    selectedOutcomeId?: string;
  };
}

export interface AppMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata?: AppMessageMetadata;
  createdAt: Date;
}