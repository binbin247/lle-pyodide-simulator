import type { GridSize, NormalizedParams } from '../types'

export const GRID_SIZES: GridSize[] = [256, 512, 1024, 2048, 4096]

export const DEFAULT_GRID_SIZE: GridSize = 512

export const DEFAULT_NORMALIZED_PARAMS: NormalizedParams = {
  alpha: -5,
  pump: 3.94,
  d2: -0.0444,
  d3: 0,
  d4: 0,
  tauR: 0,
  stepsPerFrame: 50,
}
