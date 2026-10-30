import { z } from "zod";

export const r2Schema = z.object({
  SECRET_R2_ENDPOINT: z.url(),
  SECRET_R2_BUCKET: z.string(),
  SECRET_R2_ACCESS_KEY: z.string().min(1),
  SECRET_R2_SECRET_KEY: z.string().min(1),
});

export const openaAiSchema = z.object({
  SECRET_OPENAI_API_KEY: z.string().min(1),
});

export const huggingfaceSchema = z.object({
  SECRET_HUGGINGFACE_TOKEN: z.string().min(1),
});

export const beamSchema = z.object({
  SECRET_BEAM_TOKEN: z.string().trim().min(1),
});

export const modalSchema = z.object({
  SECRET_MODAL_TOKEN_ID: z.string().trim().min(1),
  SECRET_MODAL_TOKEN_SECRET: z.string().trim().min(1),
});

export const runpodSchema = z.object({
  SECRET_RUNPOD_API_KEY: z.string().trim().min(1),
});

export const cloudflareSchema = z.object({
  SECRET_CLOUDFLARE_ACCOUNT_ID: z.string().min(1),
  SECRET_CLOUDFLARE_API_TOKEN: z.string().min(1),
});

export const secretsSchema = z.object({
  ...r2Schema.shape,
  ...beamSchema.shape,
  ...modalSchema.shape,
  ...runpodSchema.shape,
  ...openaAiSchema.shape,
  ...cloudflareSchema.shape,
  ...huggingfaceSchema.shape,
})

export type WorkspaceEnv = z.infer<typeof secretsSchema>;
