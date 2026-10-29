import { describe, expect, it } from 'vitest'
import { decodeTaskId, encodeTaskId } from './task-id'

describe('task id encoding', () => {
  it('round-trips provider and task id', () => {
    expect(decodeTaskId(encodeTaskId('beam', 'task-123'))).toEqual({ provider: 'beam', originalTaskId: 'task-123' })
  })

  it('rejects non-canonical base64', () => {
    expect(() => decodeTaskId('YmVhbTp0YXNrLTEyMw')).toThrow()
  })

  it('rejects unknown providers', () => {
    expect(() => decodeTaskId(btoa('unknown:task-123'))).toThrow()
  })

  it('rejects empty task ids', () => {
    expect(() => encodeTaskId('beam', '')).toThrow()
    expect(() => decodeTaskId(btoa('beam:'))).toThrow()
  })
})
