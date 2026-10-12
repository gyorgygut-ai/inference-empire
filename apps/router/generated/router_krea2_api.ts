export interface InferRequest {
  input: Krea2Ref2ImgInput;
  [k: string]: unknown;
}
export interface Krea2Ref2ImgInput {
  prompt: string;
  reference_image?: string | null;
  height?: number;
  width?: number;
  num_inference_steps?: number;
  guidance_scale?: number;
  seed?: number | null;
  lora_scale?: number;
  face_crop?: boolean;
  [k: string]: unknown;
}

export interface InferResponse {
  /**
   * Opaque. base64(provider:originalTaskId)
   */
  task_id: string;
  [k: string]: unknown;
}

export interface InquireResponse {
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";
  output?: Krea2Ref2ImgOutput;
  [k: string]: unknown;
}
export interface Krea2Ref2ImgOutput {
  artifact: {
    presigned_url: string;
    [k: string]: unknown;
  };
  [k: string]: unknown;
}

