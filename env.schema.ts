import { z } from "zod";

export const envSchema = z.object({
  HF_TOKEN: z.string().min(1),
  R2_ACCESS_KEY: z.string().min(1),
  R2_SECRET_KEY: z.string().min(1),
  R2_ENDPOINT: z.string().url(),
  R2_BUCKET: z.string().default("generated-media"),
});

export type WorkspaceEnv = z.infer<typeof envSchema>;

export const providerCredentialsSchema = z.object({
  BEAM_TOKEN: z.string().trim().min(1),
  RUNPOD_API_KEY: z.string().trim().min(1),
  MODAL_TOKEN_ID: z.string().trim().min(1),
  MODAL_TOKEN_SECRET: z.string().trim().min(1),
});

export const workerDeploySchemas = {
  beam: envSchema.extend(providerCredentialsSchema.pick({ BEAM_TOKEN: true }).shape),
  flash: envSchema.extend(providerCredentialsSchema.pick({ RUNPOD_API_KEY: true }).shape),
  modal: envSchema.extend(providerCredentialsSchema.pick({ MODAL_TOKEN_ID: true, MODAL_TOKEN_SECRET: true }).shape),
};
