import type { GridSize, StandardParams, StokesParams } from '../types'

export const GRID_SIZES: GridSize[] = [256, 512, 1024, 2048, 4096]

export const DEFAULT_GRID_SIZE: GridSize = 512
export const DEFAULT_STOKES_GRID_SIZE: GridSize = 1024

export const DEFAULT_STANDARD_PARAMS: StandardParams = {
  alpha: -5,
  pump: 3.94,
  d2: -0.0444,
  d3: 0,
  d4: 0,
  tauR: 0,
  dt: 0.0008,
  stepsPerFrame: 50,
}

export const DEFAULT_STOKES_PARAMS: StokesParams = {
  alphaP: 39.1,
  alphaS: 0,
  pump: 12.247,
  d2P: 0.02,
  d2S: 0.02,
  fsrMismatch: 0,
  overlap: 0.5,
  fR: 0.18,
  ramanGainP: 0.35 * 0.18 * 2,
  ramanGainS: 0.35 * 0.18 * 2,
  wavelengthRatio: 1550 / 1630,
  tauR: 0.00033,
  noise: 0.00001,
  dt: 0.00005,
  stepsPerFrame: 1000,
}
