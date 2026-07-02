/// <reference lib="webworker" />

import type {
  GridSize,
  MainToWorkerMessage,
  Metrics,
  ModelId,
  PlaticonSnapshot,
  SimulationParams,
  Snapshot,
  StandardSnapshot,
  StokesSnapshot,
  WorkerToMainMessage,
} from '../types'

declare const self: DedicatedWorkerGlobalScope

interface PyodideRuntime {
  loadPackage(packages: string | string[]): Promise<void>
  runPython(code: string): unknown
  globals: {
    set(key: string, value: unknown): void
  }
}

interface PyodideModule {
  loadPyodide(options: { indexURL: string }): Promise<PyodideRuntime>
}

const TARGET_SNAPSHOT_INTERVAL_MS = 50
const RUN_LOOP_DELAY_MS = 1

let pyodide: PyodideRuntime | null = null
let configured = false
let running = false
let loopActive = false
let currentModelId: ModelId = 'standard'
let currentN: GridSize = 512
let currentParams: SimulationParams | null = null
let stepsSinceMetric = 0
let snapshotsSinceMetric = 0
let batchesSinceMetric = 0
let batchTimeSinceMetric = 0
let latencyTimeSinceMetric = 0
let busyTimeSinceMetric = 0
let metricStartedAt = performance.now()
let lastSnapshotAt = 0

function post(message: WorkerToMainMessage, transfer?: Transferable[]) {
  self.postMessage(message, transfer ?? [])
}

self.onmessage = async (event: MessageEvent<MainToWorkerMessage>) => {
  try {
    const message = event.data
    if (message.type === 'init') {
      await initPyodide(message.pyodideUrl, message.solverUrl)
      return
    }
    if (!pyodide) {
      throw new Error('Pyodide is not ready.')
    }
    if (message.type === 'configure') {
      configure(
        message.modelId,
        message.n,
        message.params,
        message.reset ?? (currentN !== message.n || currentModelId !== message.modelId),
      )
      return
    }
    if (message.type === 'updateParams') {
      updateParams(message.modelId, message.params)
      return
    }
    if (message.type === 'start') {
      running = true
      lastSnapshotAt = 0
      void runLoop()
      return
    }
    if (message.type === 'pause') {
      running = false
      return
    }
    if (message.type === 'step') {
      running = false
      emitSnapshot(runBatch(performance.now()))
      return
    }
    if (message.type === 'reset') {
      reset()
      emitSnapshot(snapshotOnly(undefined, false))
      return
    }
    if (message.type === 'exportState') {
      const payload = runPythonAsJs('solver.export_state()')
      post({ type: 'exportState', payload })
    }
  } catch (error) {
    running = false
    post({ type: 'error', error: error instanceof Error ? error.message : String(error) })
  }
}

async function initPyodide(pyodideUrl: string, solverUrl: string) {
  post({ type: 'loading', message: 'Loading Pyodide runtime' })
  const pyodideModule = (await import(
    /* @vite-ignore */ `${pyodideUrl}/pyodide.mjs`
  )) as PyodideModule
  pyodide = await pyodideModule.loadPyodide({ indexURL: `${pyodideUrl}/` })
  post({ type: 'loading', message: 'Loading NumPy' })
  await pyodide.loadPackage('numpy')
  post({ type: 'loading', message: 'Loading LLE solver' })
  const solverSource = await fetch(solverUrl).then((response) => {
    if (!response.ok) {
      throw new Error(`Failed to fetch solver: ${response.status}`)
    }
    return response.text()
  })
  pyodide.runPython(solverSource)
  pyodide.runPython('solver = SimulationManager()')
  post({ type: 'ready' })
}

function configure(
  modelId: ModelId,
  n: GridSize,
  params: SimulationParams,
  resetState: boolean,
) {
  currentModelId = modelId
  currentN = n
  currentParams = params
  pyodide!.globals.set(
    'CONFIG_JSON',
    JSON.stringify({ modelId, n, params, reset: resetState }),
  )
  runPythonAsJs('solver.configure(json.loads(CONFIG_JSON))')
  configured = true
  emitSnapshot(snapshotOnly(undefined, false))
}

function updateParams(modelId: ModelId, params: SimulationParams) {
  if (modelId !== currentModelId) {
    configure(modelId, currentN, params, true)
    return
  }
  currentParams = params
  pyodide!.globals.set('PARAMS_JSON', JSON.stringify(params))
  runPythonAsJs('solver.update_params(json.loads(PARAMS_JSON))')
  if (!running) {
    emitSnapshot(snapshotOnly(undefined, false))
  }
}

function reset() {
  if (!configured || !currentParams) {
    return
  }
  configure(currentModelId, currentN, currentParams, true)
}

async function runLoop() {
  if (loopActive) {
    return
  }
  loopActive = true
  while (running) {
    advanceBatch()
    const now = performance.now()
    if (now - lastSnapshotAt >= TARGET_SNAPSHOT_INTERVAL_MS) {
      emitSnapshot(snapshotOnly(now))
      snapshotsSinceMetric += 1
      maybeEmitMetrics()
      lastSnapshotAt = now
    }
    await new Promise((resolve) => setTimeout(resolve, RUN_LOOP_DELAY_MS))
  }
  loopActive = false
}

function runBatch(startedAt = performance.now()): Snapshot {
  advanceBatch()
  const snapshot = snapshotOnly(startedAt)
  snapshotsSinceMetric += 1
  maybeEmitMetrics()
  return snapshot
}

function advanceBatch() {
  if (!configured) {
    throw new Error('Solver is not configured.')
  }
  const startedAt = performance.now()
  pyodide!.runPython('solver.advance_steps()')
  const batchMs = performance.now() - startedAt
  stepsSinceMetric += currentParams?.stepsPerFrame ?? 0
  batchesSinceMetric += 1
  batchTimeSinceMetric += batchMs
  busyTimeSinceMetric += batchMs
}

function snapshotOnly(startedAt = performance.now(), recordMetrics = true): Snapshot {
  const snapshotStartedAt = performance.now()
  const snapshot = normalizeSnapshot(runPythonAsJs('solver.snapshot()') as Snapshot)
  const now = performance.now()
  if (recordMetrics) {
    busyTimeSinceMetric += now - snapshotStartedAt
    latencyTimeSinceMetric += now - startedAt
  }
  return snapshot
}

function emitSnapshot(snapshot: Snapshot) {
  const transfer = snapshot.modelId === 'stokes'
    ? [
        snapshot.primaryIntensity.buffer,
        snapshot.stokesIntensity.buffer,
        snapshot.primarySpectrumDb.buffer,
        snapshot.stokesSpectrumDb.buffer,
        snapshot.primaryHistoryRow.buffer,
        snapshot.stokesHistoryRow.buffer,
      ]
    : [
        snapshot.intensity.buffer,
        snapshot.spectrumDb.buffer,
        snapshot.historyRow.buffer,
      ]
  post({ type: 'snapshot', snapshot }, transfer)
}

function maybeEmitMetrics() {
  const now = performance.now()
  const elapsed = (now - metricStartedAt) / 1000
  if (elapsed < 0.8) {
    return
  }
  const n = currentN
  const metrics: Metrics = {
    stepsPerSecond: stepsSinceMetric / elapsed,
    snapshotRate: snapshotsSinceMetric / elapsed,
    memoryMb: (n * 300 * 4 + n * 3 * 4) / 1024 / 1024,
    batchMs: batchesSinceMetric > 0 ? batchTimeSinceMetric / batchesSinceMetric : 0,
    latencyMs:
      snapshotsSinceMetric > 0 ? latencyTimeSinceMetric / snapshotsSinceMetric : 0,
    loadPercent: Math.min(100, (busyTimeSinceMetric / (elapsed * 1000)) * 100),
    n,
  }
  post({ type: 'metrics', metrics })
  stepsSinceMetric = 0
  snapshotsSinceMetric = 0
  batchesSinceMetric = 0
  batchTimeSinceMetric = 0
  latencyTimeSinceMetric = 0
  busyTimeSinceMetric = 0
  metricStartedAt = now
}

function runPythonAsJs(code: string): unknown {
  const result = pyodide!.runPython(code) as {
    toJs?: (options?: unknown) => unknown
    destroy?: () => void
  }
  if (result && typeof result.toJs === 'function') {
    const jsValue = result.toJs({ dict_converter: Object.fromEntries })
    result.destroy?.()
    return jsValue
  }
  return result
}

function normalizeSnapshot(snapshot: Snapshot): Snapshot {
  if (snapshot.modelId === 'stokes') {
    const stokesSnapshot = snapshot as StokesSnapshot
    return {
      ...stokesSnapshot,
      primaryIntensity: toFloat32Array(stokesSnapshot.primaryIntensity),
      stokesIntensity: toFloat32Array(stokesSnapshot.stokesIntensity),
      primarySpectrumDb: toFloat32Array(stokesSnapshot.primarySpectrumDb),
      stokesSpectrumDb: toFloat32Array(stokesSnapshot.stokesSpectrumDb),
      primaryHistoryRow: toFloat32Array(stokesSnapshot.primaryHistoryRow),
      stokesHistoryRow: toFloat32Array(stokesSnapshot.stokesHistoryRow),
    }
  }
  const standardSnapshot = snapshot as StandardSnapshot | PlaticonSnapshot
  return {
    ...standardSnapshot,
    intensity: toFloat32Array(standardSnapshot.intensity),
    spectrumDb: toFloat32Array(standardSnapshot.spectrumDb),
    historyRow: toFloat32Array(standardSnapshot.historyRow),
  }
}

function toFloat32Array(value: unknown): Float32Array {
  if (value instanceof Float32Array) {
    return new Float32Array(value)
  }
  if (ArrayBuffer.isView(value)) {
    return new Float32Array(Array.from(value as unknown as ArrayLike<number>))
  }
  return new Float32Array(value as ArrayLike<number>)
}
