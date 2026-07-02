import type {
  GridSize,
  MulticolorParams,
  PlaticonParams,
  RamanParams,
  StandardParams,
  StokesParams,
  TurnkeyParams,
} from '../types'

export const GRID_SIZES: GridSize[] = [256, 512, 1024, 2048, 4096]

export const DEFAULT_GRID_SIZE: GridSize = 512
export const DEFAULT_PLATICON_GRID_SIZE: GridSize = 512
export const DEFAULT_STOKES_GRID_SIZE: GridSize = 1024
export const DEFAULT_TURNKEY_GRID_SIZE: GridSize = 512
export const DEFAULT_MULTICOLOR_GRID_SIZE: GridSize = 1024
export const DEFAULT_RAMAN_GRID_SIZE: GridSize = 512

export const DEFAULT_STANDARD_PARAMS: StandardParams = {
  alpha: 10,
  pump: 3.94,
  d2: -0.0444,
  d3: 0,
  d4: 0,
  tauR: 0,
  dt: 0.0008,
  stepsPerFrame: 50,
}

export const DEFAULT_PLATICON_PARAMS: PlaticonParams = {
  alpha: 4,
  pump: 3.94,
  d2: 0.02,
  modeShiftMu: 0,
  modeShiftStrength: 4,
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

export const DEFAULT_TURNKEY_PARAMS: TurnkeyParams = {
  laserDetuning: 5,
  pump: Math.sqrt(3),
  d2: 0.015,
  beta: 0.5,
  lockingBandwidth: 15,
  feedbackPhase: 0.3 * Math.PI,
  noise: 0.00001,
  dt: 0.0005,
  stepsPerFrame: 200,
}

export const DEFAULT_MULTICOLOR_PARAMS: MulticolorParams = {
  alphaP: 48,
  alphaS: 25,
  alphaI: 25,
  pump: 17,
  d2P: 0.201,
  d2S: 0.0905,
  d2I: -0.0877,
  fsrMismatchS: 0,
  fsrMismatchI: 18.1,
  xpm: 1.73 / 4.33,
  fwmRe: 1.73 / 4.33,
  fwmIm: 0,
  noise: 0.00001,
  dt: 0.00002,
  stepsPerFrame: 500,
}

export const DEFAULT_RAMAN_PARAMS: RamanParams = {
  dtnNorm: 11.829136663739904,
  ffNorm: 9.784017373364096,
  d2Norm: 1.65414364640884,
  fR: 0.02,
  tau1Fs: 11.1,
  tau2Fs: 35,
  fsrGHz: 1000,
  qMillion: 4,
  wavelengthNm: 1550,
  noise: 0.0001,
  dt: 0.00005,
  stepsPerFrame: 1000,
}
