export type Language = 'en' | 'zh'

export type GridSize = 256 | 512 | 1024 | 2048 | 4096

export interface NormalizedParams {
  alpha: number
  pump: number
  d2: number
  d3: number
  d4: number
  tauR: number
  stepsPerFrame: number
}

export interface SolverParams extends NormalizedParams {
  dt: number
}

export interface Metrics {
  stepsPerSecond: number
  snapshotRate: number
  memoryMb: number
  batchMs: number
  latencyMs: number
  loadPercent: number
  n: number
}

export interface Snapshot {
  step: number
  t: number
  intensity: Float32Array
  spectrumDb: Float32Array
  historyRow: Float32Array
  energy: number
  peak: number
  normalizedParams: SolverParams
}

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
  n: GridSize
  params: NormalizedParams
  reset?: boolean
}

export interface WorkerUpdateParamsMessage {
  type: 'updateParams'
  params: NormalizedParams
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
