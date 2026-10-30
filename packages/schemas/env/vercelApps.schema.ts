import { z } from 'zod'
import { api as vercelSchema } from './vercel.schema'

type PrefixedShape<Prefix extends string, Shape extends z.ZodRawShape> = {
  [Key in keyof Shape as `${Prefix}${Key & string}`]: Shape[Key]
}

const prefixSchema = <const Prefix extends string, Shape extends z.ZodRawShape>(
  prefix: Prefix,
  schema: z.ZodObject<Shape>,
) => {
  const shape = Object.fromEntries(
    Object.entries(schema.shape).map(([key, field]) => [`${prefix}${key}`, field]),
  ) as PrefixedShape<Prefix, Shape>
  return z.object(shape)
}

export const faceValueSchema = prefixSchema('SECRET_FACE_VALUE_', vercelSchema)
export const voiceChatSchema = prefixSchema('SECRET_VOICE_CHAT_', vercelSchema)
