import { describe, expect, it } from 'vitest'
import {
  DEFAULT_PLATICON_GRID_SIZE,
  DEFAULT_PLATICON_PARAMS,
  DEFAULT_STANDARD_PARAMS,
  DEFAULT_STOKES_GRID_SIZE,
  DEFAULT_STOKES_PARAMS,
} from './defaults'
import { MODEL_IDS } from './models'
import { clampParamsForModel, clampPlaticonParams, clampStandardParams } from './physics'

describe('parameter clamping', () => {
  it('keeps finite normalized controls and clamps invalid values', () => {
    const params = clampStandardParams({
      alpha: Number.NaN,
      pump: -1,
      d2: -0.0444,
      d3: 0,
      d4: 0,
      tauR: 0.01,
      dt: Number.POSITIVE_INFINITY,
      stepsPerFrame: 10.4,
    })

    expect(params.alpha).toBe(0)
    expect(params.pump).toBe(0)
    expect(params.d2).toBe(-0.0444)
    expect(params.dt).toBe(0.0008)
    expect(params.stepsPerFrame).toBe(10)
  })

  it('keeps Stokes controls finite and inside interactive ranges', () => {
    const params = clampParamsForModel('stokes', {
      alphaP: Number.POSITIVE_INFINITY,
      alphaS: -30,
      pump: -5,
      d2P: 1,
      d2S: -1,
      fsrMismatch: 4,
      overlap: 3,
      fR: Number.NaN,
      ramanGainP: 4,
      ramanGainS: -1,
      wavelengthRatio: 4,
      tauR: -1,
      noise: 1,
      dt: Number.POSITIVE_INFINITY,
      stepsPerFrame: 9.6,
    })

    expect(params).toMatchObject({
      alphaP: 39.1,
      alphaS: 0,
      pump: 0,
      d2P: 0.25,
      d2S: -0.25,
      fsrMismatch: 1,
      overlap: 2,
      fR: 0.18,
      ramanGainP: 2,
      ramanGainS: 0,
      wavelengthRatio: 1.5,
      tauR: 0,
      noise: 0.001,
      dt: 0.00005,
      stepsPerFrame: 10,
    })
  })

  it('orders models with platicon between standard and Stokes', () => {
    expect(MODEL_IDS).toEqual(['standard', 'platicon', 'stokes'])
  })

  it('keeps platicon controls finite and inside interactive ranges', () => {
    const params = clampParamsForModel('platicon', {
      alpha: Number.POSITIVE_INFINITY,
      pump: -5,
      d2: 2,
      modeShiftMu: 7.6,
      modeShiftStrength: -30,
      dt: Number.POSITIVE_INFINITY,
      stepsPerFrame: Number.NaN,
    })

    expect(params).toMatchObject({
      alpha: DEFAULT_PLATICON_PARAMS.alpha,
      pump: 0,
      d2: 0.25,
      modeShiftMu: 8,
      modeShiftStrength: -20,
      dt: DEFAULT_PLATICON_PARAMS.dt,
      stepsPerFrame: DEFAULT_PLATICON_PARAMS.stepsPerFrame,
    })
  })

  it('uses platicon dark-pulse defaults', () => {
    expect(DEFAULT_PLATICON_GRID_SIZE).toBe(512)
    expect(DEFAULT_PLATICON_PARAMS).toMatchObject({
      alpha: 4,
      pump: 3.94,
      d2: 0.02,
      modeShiftMu: 0,
      modeShiftStrength: 4,
      dt: 0.0008,
      stepsPerFrame: 50,
    })
  })

  it('clamps platicon mode shift to the selected grid', () => {
    const high = clampPlaticonParams({ ...DEFAULT_PLATICON_PARAMS, modeShiftMu: 9999 }, 256)
    const low = clampPlaticonParams({ ...DEFAULT_PLATICON_PARAMS, modeShiftMu: -9999 }, 256)

    expect(high.modeShiftMu).toBe(127)
    expect(low.modeShiftMu).toBe(-128)
  })

  it('keeps Stokes system defaults aligned with the MATLAB scan script', () => {
    expect(DEFAULT_STOKES_PARAMS.alphaP).toBe(39.1)
    expect(DEFAULT_STOKES_PARAMS.overlap).toBe(0.5)
    expect(DEFAULT_STOKES_PARAMS.fR).toBe(0.18)
    expect(DEFAULT_STOKES_PARAMS.ramanGainP).toBeCloseTo(0.35 * 0.18 * 2)
    expect(DEFAULT_STOKES_PARAMS.ramanGainS).toBeCloseTo(0.35 * 0.18 * 2)
    expect(DEFAULT_STOKES_PARAMS.wavelengthRatio).toBeCloseTo(1550 / 1630)
    expect(DEFAULT_STOKES_PARAMS.tauR).toBe(0.00033)
    expect(DEFAULT_STOKES_PARAMS.stepsPerFrame).toBe(1000)
    expect(DEFAULT_STOKES_GRID_SIZE).toBe(1024)
  })

  it('uses a soliton-ready default detuning for the standard model', () => {
    expect(DEFAULT_STANDARD_PARAMS.alpha).toBe(10)
  })

  it('uses the Stokes default stride when Stokes steps per frame is invalid', () => {
    const params = clampParamsForModel('stokes', {
      ...DEFAULT_STOKES_PARAMS,
      stepsPerFrame: Number.NaN,
    })

    expect(params.stepsPerFrame).toBe(1000)
  })
})
