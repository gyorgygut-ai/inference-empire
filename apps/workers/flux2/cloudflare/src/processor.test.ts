import { describe, expect, it } from 'vitest'
import {
  processGeneration,
  toWorkersAiForm,
  type Flux2Input,
  type GenerationDependencies,
  type TaskRecord,
} from './processor'

const input: Flux2Input = {
  prompt: 'mountain lake at sunrise',
  height: 512,
  width: 512,
  guidance_scale: 1,
  num_inference_steps: 4,
  seed: 17,
  input_image: null,
  reference_images: [],
}

class GenerationStub implements GenerationDependencies {
  readonly transitions: TaskRecord[] = []
  readonly artifacts: Array<{ key: string; bytes: Uint8Array; contentType: string }> = []
  record: TaskRecord | null = { status: 'PENDING' }

  constructor(private readonly image = 'iVBORw0KGgoBAgM=', private readonly modelFailure?: Error) {}

  async getTask(): Promise<TaskRecord | null> {
    return this.record
  }

  async setTask(_taskId: string, record: TaskRecord): Promise<void> {
    this.record = record
    this.transitions.push(record)
  }

  async runModel(): Promise<string> {
    if (this.modelFailure) {throw this.modelFailure}
    return this.image
  }

  async putArtifact(key: string, bytes: Uint8Array, contentType: 'image/png' | 'image/jpeg'): Promise<void> {
    this.artifacts.push({ key, bytes, contentType })
  }
}

describe('toWorkersAiForm', () => {
  it('maps contract settings to multipart fields', async () => {
    const multipart = toWorkersAiForm(input)
    const response = new Response(multipart.body, { headers: { 'Content-Type': multipart.contentType } })
    const form = await response.formData()

    expect(Object.fromEntries(['prompt', 'width', 'height', 'guidance', 'seed'].map((key) => [key, form.get(key)]))).toEqual({
      prompt: input.prompt,
      width: String(input.width),
      height: String(input.height),
      guidance: String(input.guidance_scale),
      seed: String(input.seed),
    })
  })

  it('rejects dimensions outside the Workers AI model range', () => {
    const failure = (() => {
      try { toWorkersAiForm({ ...input, width: 2048 }); return null }
      catch (error) { return error instanceof Error ? error.message : String(error) }
    })()

    expect(failure).toContain('between 256 and 1920')
  })

  it('rejects inference steps unsupported by FLUX.2 Klein', () => {
    const failure = (() => {
      try { toWorkersAiForm({ ...input, num_inference_steps: 8 }); return null }
      catch (error) { return error instanceof Error ? error.message : String(error) }
    })()

    expect(failure).toContain('exactly 4')
  })

  it('maps four image references to indexed multipart image fields', async () => {
    const multipart = toWorkersAiForm({
      ...input,
      input_image: 'AQID',
      reference_images: ['BAUG', 'BwgJ', 'CgsM'],
    })
    const response = new Response(multipart.body, { headers: { 'Content-Type': multipart.contentType } })
    const form = await response.formData()

    expect(Object.fromEntries([0, 1, 2, 3].map((index) => [`input_image_${index}`, form.getAll(`input_image_${index}`).length]))).toEqual({
      input_image_0: 1,
      input_image_1: 1,
      input_image_2: 1,
      input_image_3: 1,
    })
  })

  it('rejects more image references than Workers AI accepts', () => {
    const failure = (() => {
      try {
        toWorkersAiForm({ ...input, reference_images: ['AQ==', 'Ag==', 'Aw==', 'BA==', 'BQ=='] })
        return null
      } catch (error) { return error instanceof Error ? error.message : String(error) }
    })()

    expect(failure).toContain('at most 4')
  })
})

describe('processGeneration', () => {
  it('stores the generated image and completes task state', async () => {
    const dependencies = new GenerationStub()
    await processGeneration('task-1', input, dependencies)

    expect({
      transitions: dependencies.transitions,
      artifacts: dependencies.artifacts,
    }).toEqual({
      transitions: [
        { status: 'PROCESSING' },
        { status: 'COMPLETED', artifactKey: 'flux2/task-1.png', contentType: 'image/png' },
      ],
      artifacts: [{ key: 'flux2/task-1.png', bytes: Uint8Array.from([137, 80, 78, 71, 13, 10, 26, 10, 1, 2, 3]), contentType: 'image/png' }],
    })
  })

  it('leaves completed tasks unchanged on duplicate queue delivery', async () => {
    const dependencies = new GenerationStub('iVBORw0KGgoBAgM=')
    dependencies.record = { status: 'COMPLETED', artifactKey: 'flux2/task-2.png', contentType: 'image/png' }

    await processGeneration('task-2', input, dependencies)

    expect({ record: dependencies.record, transitions: dependencies.transitions, artifacts: dependencies.artifacts }).toEqual({
      record: { status: 'COMPLETED', artifactKey: 'flux2/task-2.png', contentType: 'image/png' },
      transitions: [],
      artifacts: [],
    })
  })

  it('keeps a failed inference from marking the task complete', async () => {
    const dependencies = new GenerationStub('AQID', new Error('model unavailable'))
    const failure = await processGeneration('task-3', input, dependencies)
      .then(() => null, (error: unknown) => error instanceof Error ? error.message : String(error))

    expect({ failure, transitions: dependencies.transitions, artifactCount: dependencies.artifacts.length }).toEqual({
      failure: 'model unavailable',
      transitions: [{ status: 'PROCESSING' }],
      artifactCount: 0,
    })
  })

  it('stores JPEG output with a matching extension and media type', async () => {
    const dependencies = new GenerationStub('/9j/AA==')
    await processGeneration('task-jpeg', input, dependencies)

    expect({ record: dependencies.record, artifact: dependencies.artifacts[0] }).toEqual({
      record: { status: 'COMPLETED', artifactKey: 'flux2/task-jpeg.jpg', contentType: 'image/jpeg' },
      artifact: { key: 'flux2/task-jpeg.jpg', bytes: Uint8Array.from([255, 216, 255, 0]), contentType: 'image/jpeg' },
    })
  })
})
