import type { NormalizedParams } from '../types'

export function clampNormalizedParams(params: NormalizedParams): NormalizedParams {
  return {
    alpha: finiteOr(params.alpha, 0),
    pump: Math.max(0, finiteOr(params.pump, 0)),
    d2: finiteOr(params.d2, 0),
    d3: finiteOr(params.d3, 0),
    d4: finiteOr(params.d4, 0),
    tauR: finiteOr(params.tauR, 0),
    stepsPerFrame: Math.max(1, Math.round(finiteOr(params.stepsPerFrame, 50))),
  }
}

function finiteOr(value: number, fallback: number): number {
  return Number.isFinite(value) ? value : fallback
}
