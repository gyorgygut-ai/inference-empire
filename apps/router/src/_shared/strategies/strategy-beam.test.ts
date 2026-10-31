import { describe, expect, it, vi } from 'vitest'
import type { RuntimeConfig } from '../config'
import { strategyBeam } from './strategy-beam'

const config: RuntimeConfig = {
  routerToken: 'router-token',
  beamUrl: 'https://worker.beam.cloud/taskqueue',
  beamToken: 'beam-token',
}

describe('strategyBeam', () => {
  it('reads the handler result from Beam task API and preserves TinySD output shape', async () => {
    const output = { artifact: { presigned_url: 'https://artifacts.example/image.png' } }
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(Response.json({ external_id: 'workspace-id' }))
      .mockResolvedValueOnce(Response.json({ status: 'COMPLETE', result: output, outputs: [] }))
    const strategy = strategyBeam(config, fetchImpl)

    const result = await strategy.fetchTaskStatus('task/id')

    expect(fetchImpl).toHaveBeenNthCalledWith(1, 'https://app.beam.cloud/api/v1/workspace/current', {
      headers: { Authorization: 'Bearer beam-token' },
    })
    expect(fetchImpl).toHaveBeenNthCalledWith(2, 'https://app.beam.cloud/api/v1/task/workspace-id/task%2Fid', {
      headers: { Authorization: 'Bearer beam-token' },
    })
    expect(result).toEqual({ status: 'COMPLETED', output })
  })
})
