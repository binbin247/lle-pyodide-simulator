import type {
  GridSize,
  ModelId,
  PlaticonParams,
  SimulationParams,
  StandardParams,
  StokesParams,
} from '../types'
import {
  DEFAULT_PLATICON_PARAMS,
  DEFAULT_STANDARD_PARAMS,
  DEFAULT_STOKES_PARAMS,
} from './defaults'

export function clampParamsForModel(
  modelId: ModelId,
  params: SimulationParams,
): SimulationParams {
  if (modelId === 'stokes') {
    return clampStokesParams(params as StokesParams)
  }
  if (modelId === 'platicon') {
    return clampPlaticonParams(params as PlaticonParams)
  }
  return clampStandardParams(params as StandardParams)
}

export function clampStandardParams(params: StandardParams): StandardParams {
  return {
    alpha: finiteOr(params.alpha, 0),
    pump: Math.max(0, finiteOr(params.pump, 0)),
    d2: finiteOr(params.d2, 0),
    d3: finiteOr(params.d3, 0),
    d4: finiteOr(params.d4, 0),
    tauR: finiteOr(params.tauR, 0),
    dt: clamp(finiteOr(params.dt, DEFAULT_STANDARD_PARAMS.dt), 1e-12, 0.005),
    stepsPerFrame: Math.max(
      1,
      Math.round(finiteOr(params.stepsPerFrame, DEFAULT_STANDARD_PARAMS.stepsPerFrame)),
    ),
  }
}

export function clampPlaticonParams(
  params: PlaticonParams,
  gridSize: GridSize = 4096,
): PlaticonParams {
  const { minMu, maxMu } = modeShiftBounds(gridSize)
  return {
    alpha: clamp(finiteOr(params.alpha, DEFAULT_PLATICON_PARAMS.alpha), -20, 40),
    pump: clamp(finiteOr(params.pump, DEFAULT_PLATICON_PARAMS.pump), 0, 12),
    d2: clamp(finiteOr(params.d2, DEFAULT_PLATICON_PARAMS.d2), -0.25, 0.25),
    modeShiftMu: Math.round(
      clamp(finiteOr(params.modeShiftMu, DEFAULT_PLATICON_PARAMS.modeShiftMu), minMu, maxMu),
    ),
    modeShiftStrength: clamp(
      finiteOr(params.modeShiftStrength, DEFAULT_PLATICON_PARAMS.modeShiftStrength),
      -20,
      20,
    ),
    dt: clamp(finiteOr(params.dt, DEFAULT_PLATICON_PARAMS.dt), 1e-12, 0.005),
    stepsPerFrame: Math.max(
      1,
      Math.round(finiteOr(params.stepsPerFrame, DEFAULT_PLATICON_PARAMS.stepsPerFrame)),
    ),
  }
}

export function modeShiftBounds(gridSize: GridSize) {
  const half = Math.floor(gridSize / 2)
  return { minMu: -half, maxMu: half - 1 }
}

export function clampStokesParams(params: StokesParams): StokesParams {
  return {
    alphaP: clamp(finiteOr(params.alphaP, DEFAULT_STOKES_PARAMS.alphaP), -20, 100),
    alphaS: 0,
    pump: clamp(finiteOr(params.pump, DEFAULT_STOKES_PARAMS.pump), 0, 40),
    d2P: clamp(finiteOr(params.d2P, DEFAULT_STOKES_PARAMS.d2P), -0.25, 0.25),
    d2S: clamp(finiteOr(params.d2S, DEFAULT_STOKES_PARAMS.d2S), -0.25, 0.25),
    fsrMismatch: clamp(
      finiteOr(params.fsrMismatch, DEFAULT_STOKES_PARAMS.fsrMismatch),
      -1,
      1,
    ),
    overlap: clamp(finiteOr(params.overlap, DEFAULT_STOKES_PARAMS.overlap), 0, 2),
    fR: clamp(finiteOr(params.fR, DEFAULT_STOKES_PARAMS.fR), 0, 1),
    ramanGainP: clamp(
      finiteOr(params.ramanGainP, DEFAULT_STOKES_PARAMS.ramanGainP),
      0,
      2,
    ),
    ramanGainS: clamp(
      finiteOr(params.ramanGainS, DEFAULT_STOKES_PARAMS.ramanGainS),
      0,
      2,
    ),
    wavelengthRatio: clamp(
      finiteOr(params.wavelengthRatio, DEFAULT_STOKES_PARAMS.wavelengthRatio),
      0.5,
      1.5,
    ),
    tauR: clamp(finiteOr(params.tauR, DEFAULT_STOKES_PARAMS.tauR), 0, 0.02),
    noise: clamp(finiteOr(params.noise, DEFAULT_STOKES_PARAMS.noise), 0, 0.001),
    dt: clamp(finiteOr(params.dt, DEFAULT_STOKES_PARAMS.dt), 1e-12, 0.005),
    stepsPerFrame: Math.max(
      1,
      Math.round(finiteOr(params.stepsPerFrame, DEFAULT_STOKES_PARAMS.stepsPerFrame)),
    ),
  }
}

export const clampNormalizedParams = clampStandardParams

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function finiteOr(value: number, fallback: number): number {
  return Number.isFinite(value) ? value : fallback
}
