export interface AddToQueueRequest {
  input: Flux2Klein9BInput;
  [k: string]: unknown;
}
export interface Flux2Klein9BInput {
  prompt: string;
  height?: number;
  width?: number;
  guidance_scale?: number;
  num_inference_steps?: number;
  seed?: number | null;
  input_image?: string | null;
  reference_images?: string[];
  [k: string]: unknown;
}

export interface AddToQueueResponse {
  /**
   * Opaque. base64(provider:originalTaskId)
   */
  task_id: string;
  [k: string]: unknown;
}

export interface SupResponse {
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";
  output?: Flux2Klein9BOutput;
  [k: string]: unknown;
}
export interface Flux2Klein9BOutput {
  artifact: {
    presigned_url: string;
    [k: string]: unknown;
  };
  [k: string]: unknown;
}

