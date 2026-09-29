/* Generated from dist/apps/flux2/contract.json (.input/.output, emitted by flux2-router-worker deploy). Do not edit directly. */

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

export interface Flux2Klein9BOutput {
  artifact: {
    presigned_url: string;
  };
  [k: string]: unknown;
}
