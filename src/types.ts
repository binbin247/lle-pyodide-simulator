export type Language = 'en' | 'zh'

export type GridSize = 256 | 512 | 1024 | 2048 | 4096

export type ModelId = 'standard' | 'platicon' | 'stokes'

export interface StandardParams {
  alpha: number
  pump: number
  d2: number
  d3: number
  d4: number
  tauR: number
  dt: number
  stepsPerFrame: number
}

export interface PlaticonParams {
  alpha: number
  pump: number
  d2: number
  modeShiftMu: number
  modeShiftStrength: number
  dt: number
  stepsPerFrame: number
}

export interface StokesParams {
  alphaP: number
  alphaS: number
  pump: number
  d2P: number
  d2S: number
  fsrMismatch: number
  overlap: number
  fR: number
  ramanGainP: number
  ramanGainS: number
  wavelengthRatio: number
  tauR: number
  noise: number
  dt: number
  stepsPerFrame: number
}

export type SimulationParams = StandardParams | PlaticonParams | StokesParams

export interface Metrics {
  stepsPerSecond: number
  snapshotRate: number
  memoryMb: number
  batchMs: number
  latencyMs: number
  loadPercent: number
  n: number
}

export interface StandardSnapshot {
  modelId: 'standard'
  step: number
  t: number
  intensity: Float32Array
  spectrumDb: Float32Array
  historyRow: Float32Array
  energy: number
  peak: number
  normalizedParams: StandardParams
}

export interface PlaticonSnapshot {
  modelId: 'platicon'
  step: number
  t: number
  intensity: Float32Array
  spectrumDb: Float32Array
  historyRow: Float32Array
  energy: number
  peak: number
  normalizedParams: PlaticonParams
}

export interface StokesSnapshot {
  modelId: 'stokes'
  step: number
  t: number
  primaryIntensity: Float32Array
  stokesIntensity: Float32Array
  primarySpectrumDb: Float32Array
  stokesSpectrumDb: Float32Array
  primaryHistoryRow: Float32Array
  stokesHistoryRow: Float32Array
  primaryEnergy: number
  stokesEnergy: number
  primaryPeak: number
  stokesPeak: number
  normalizedParams: StokesParams
}

export type Snapshot = StandardSnapshot | PlaticonSnapshot | StokesSnapshot

export type WorkerStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'running'
  | 'paused'
  | 'error'

export interface WorkerInitMessage {
  type: 'init'
  pyodideUrl: string
  solverUrl: string
}

export interface WorkerConfigureMessage {
  type: 'configure'
  modelId: ModelId
  n: GridSize
  params: SimulationParams
  reset?: boolean
}

export interface WorkerUpdateParamsMessage {
  type: 'updateParams'
  modelId: ModelId
  params: SimulationParams
}

export interface WorkerControlMessage {
  type: 'start' | 'pause' | 'step' | 'reset' | 'exportState'
}

export type MainToWorkerMessage =
  | WorkerInitMessage
  | WorkerConfigureMessage
  | WorkerUpdateParamsMessage
  | WorkerControlMessage

export type WorkerToMainMessage =
  | { type: 'loading'; message: string }
  | { type: 'ready' }
  | { type: 'snapshot'; snapshot: Snapshot }
  | { type: 'metrics'; metrics: Metrics }
  | { type: 'exportState'; payload: unknown }
  | { type: 'error'; error: string }
