import { describe, expect, it } from 'vitest'
import { clampNormalizedParams } from './physics'

describe('clampNormalizedParams', () => {
  it('keeps finite normalized controls and clamps invalid values', () => {
    const params = clampNormalizedParams({
      alpha: Number.NaN,
      pump: -1,
      d2: -0.0444,
      d3: 0,
      d4: 0,
      tauR: 0.01,
      dt: 0,
      stepsPerFrame: 10.4,
    })

    expect(params.alpha).toBe(0)
    expect(params.pump).toBe(0)
    expect(params.d2).toBe(-0.0444)
    expect(params.dt).toBe(1e-7)
    expect(params.stepsPerFrame).toBe(10)
  })
})
