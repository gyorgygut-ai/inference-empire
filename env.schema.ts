import { z } from "zod";

export const envSchema = z.object({
  HF_TOKEN: z.string().min(1),
  R2_ACCESS_KEY: z.string().min(1),
  R2_SECRET_KEY: z.string().min(1),
  R2_ENDPOINT: z.string().url(),
  R2_BUCKET: z.string().default("generated-media"),
});

export type WorkspaceEnv = z.infer<typeof envSchema>;
