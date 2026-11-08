import { z } from 'zod'
import { api as r2Schema } from './env/r2.schema'
import { api as openAiSchema } from './env/openAi.schema'
import { api as elevenLabsSchema } from './env/elevenLabs.schema'
import { api as huggingfaceSchema } from './env/huggingface.schema'
import { api as beamSchema } from './env/beam.schema'
import { api as modalSchema } from './env/modal.schema'
import { api as runpodSchema } from './env/runpod.schema'
import { api as cloudflareSchema } from './env/cloudflare.schema'
import { faceValueSchema, voiceChatSchema } from './env/vercelApps.schema'

export const secretsSchema = z.object({
  ...r2Schema.shape,
  ...openAiSchema.shape,
  ...elevenLabsSchema.shape,
  ...huggingfaceSchema.shape,
  ...beamSchema.shape,
  ...modalSchema.shape,
  ...runpodSchema.shape,
  ...cloudflareSchema.shape,
  ...faceValueSchema.shape,
  ...voiceChatSchema.shape,
}).partial()

export const devSecretsSchema = z.object({
  ...r2Schema.shape,
  ...openAiSchema.shape,
  ...elevenLabsSchema.shape,
  ...huggingfaceSchema.shape,
  ...beamSchema.shape,
})

export const deploySecretsSchema = z.object({
  ...r2Schema.shape,
  ...openAiSchema.shape,
  ...elevenLabsSchema.shape,
  ...huggingfaceSchema.shape,
  ...beamSchema.shape,
  ...modalSchema.shape,
  ...runpodSchema.shape,
  ...cloudflareSchema.shape,
  ...faceValueSchema.shape,
  ...voiceChatSchema.shape,
})

export type WorkspaceSecrets = z.infer<typeof secretsSchema>
