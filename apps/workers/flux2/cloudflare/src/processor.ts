import { z } from 'zod'
import type { Api } from '../dist/flux2.schema'

export const taskRecordSchema = z.discriminatedUnion('status', [
  z.object({ status: z.enum(['PENDING', 'PROCESSING']) }),
  z.object({
    status: z.literal('COMPLETED'),
    artifactKey: z.string().min(1),
    contentType: z.enum(['image/png', 'image/jpeg']).default('image/png'),
  }),
  z.object({ status: z.literal('FAILED'), error: z.string().min(1) }),
])

export type Flux2Input = Api['input']
export type TaskRecord = z.infer<typeof taskRecordSchema>

export interface GenerationDependencies {
  getTask(taskId: string): Promise<TaskRecord | null>
  setTask(taskId: string, record: TaskRecord): Promise<void>
  runModel(input: Flux2Input): Promise<string>
  putArtifact(key: string, bytes: Uint8Array, contentType: 'image/png' | 'image/jpeg'): Promise<void>
}

export function validateWorkersAiInput(input: Flux2Input): void {
  if (input.width < 256 || input.width > 1920 || input.height < 256 || input.height > 1920) {
    throw new Error('FLUX.2 dimensions must be between 256 and 1920 pixels')
  }
  if (input.num_inference_steps !== 4) {
    throw new Error('Cloudflare FLUX.2 Klein supports exactly 4 inference steps')
  }

  const images = [input.input_image, ...input.reference_images].filter((image): image is string => image !== null)
  if (images.length > 4) {throw new Error('Cloudflare FLUX.2 accepts at most 4 reference images')}
}

export function toWorkersAiForm(input: Flux2Input): { body: ReadableStream<Uint8Array>; contentType: string } {
  validateWorkersAiInput(input)
  const images = [input.input_image, ...input.reference_images].filter((image): image is string => image !== null)
  const form = new FormData()
  form.set('prompt', input.prompt)
  form.set('width', String(input.width))
  form.set('height', String(input.height))
  form.set('guidance', String(input.guidance_scale))
  if (input.seed !== null) {form.set('seed', String(input.seed))}

  images.forEach((image, index) => {
    const [metadata, data] = image.startsWith('data:') ? image.split(',', 2) : ['', image]
    if (!data) {throw new Error(`Image ${index} is not valid base64 data`)}
    const mediaType = metadata.match(/^data:([^;]+);base64$/)?.[1] ?? 'image/png'
    let binary: string
    try { binary = atob(data) }
    catch { throw new Error(`Image ${index} is not valid base64 data`) }
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0))
    form.set(`input_image_${index}`, new Blob([bytes.buffer], { type: mediaType }))
  })

  const serialized = new Response(form)
  const contentType = serialized.headers.get('content-type')
  if (!serialized.body || !contentType) {throw new Error('Could not serialize FLUX.2 multipart input')}
  return { body: serialized.body, contentType }
}

export async function processGeneration(
  taskId: string,
  input: Flux2Input,
  dependencies: GenerationDependencies,
): Promise<void> {
  const existing = await dependencies.getTask(taskId)
  if (existing?.status === 'COMPLETED' || existing?.status === 'FAILED') {return}

  await dependencies.setTask(taskId, { status: 'PROCESSING' })
  const image = await dependencies.runModel(input)
  let binary: string
  try { binary = atob(image) }
  catch { throw new Error('Workers AI returned invalid base64 image data') }
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0))
  if (!bytes.byteLength) {throw new Error('Workers AI returned an empty image')}

  const isPng = bytes.length >= 8 && bytes.subarray(0, 8).every((byte, index) => byte === [137, 80, 78, 71, 13, 10, 26, 10][index])
  const isJpeg = bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff
  if (!isPng && !isJpeg) {throw new Error('Workers AI returned an unsupported image format')}

  const contentType = isPng ? 'image/png' : 'image/jpeg'
  const extension = isPng ? 'png' : 'jpg'
  const artifactKey = `flux2/${taskId}.${extension}`
  await dependencies.putArtifact(artifactKey, bytes, contentType)
  await dependencies.setTask(taskId, { status: 'COMPLETED', artifactKey, contentType })
}
