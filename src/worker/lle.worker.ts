/// <reference lib="webworker" />

import type {
  GridSize,
  MainToWorkerMessage,
  Metrics,
  NormalizedParams,
  Snapshot,
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
let currentN: GridSize = 512
let currentParams: NormalizedParams | null = null
let stepsSinceMetric = 0
let snapshotsSinceMetric = 0
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
      configure(message.n, message.params, message.reset ?? currentN !== message.n)
      return
    }
    if (message.type === 'updateParams') {
      updateParams(message.params)
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
      emitSnapshot(runBatch())
      return
    }
    if (message.type === 'reset') {
      reset()
      emitSnapshot(snapshotOnly())
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
  pyodide.runPython('solver = LLESolver()')
  post({ type: 'ready' })
}

function configure(n: GridSize, params: NormalizedParams, resetState: boolean) {
  currentN = n
  currentParams = params
  pyodide!.globals.set('CONFIG_JSON', JSON.stringify({ n, params, reset: resetState }))
  runPythonAsJs('solver.configure(json.loads(CONFIG_JSON))')
  configured = true
  emitSnapshot(snapshotOnly())
}

function updateParams(params: NormalizedParams) {
  currentParams = params
  pyodide!.globals.set('PARAMS_JSON', JSON.stringify(params))
  runPythonAsJs('solver.update_params(json.loads(PARAMS_JSON))')
  if (!running) {
    emitSnapshot(snapshotOnly())
  }
}

function reset() {
  if (!configured || !currentParams) {
    return
  }
  configure(currentN, currentParams, true)
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
      emitSnapshot(snapshotOnly())
      snapshotsSinceMetric += 1
      maybeEmitMetrics()
      lastSnapshotAt = now
    }
    await new Promise((resolve) => setTimeout(resolve, RUN_LOOP_DELAY_MS))
  }
  loopActive = false
}

function runBatch(): Snapshot {
  advanceBatch()
  snapshotsSinceMetric += 1
  maybeEmitMetrics()
  return snapshotOnly()
}

function advanceBatch() {
  if (!configured) {
    throw new Error('Solver is not configured.')
  }
  pyodide!.runPython('solver.advance_steps()')
  stepsSinceMetric += currentParams?.stepsPerFrame ?? 0
}

function snapshotOnly(): Snapshot {
  return normalizeSnapshot(runPythonAsJs('solver.snapshot()') as Snapshot)
}

function emitSnapshot(snapshot: Snapshot) {
  const transfer = [
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
    n,
  }
  post({ type: 'metrics', metrics })
  stepsSinceMetric = 0
  snapshotsSinceMetric = 0
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
  return {
    ...snapshot,
    intensity: toFloat32Array(snapshot.intensity),
    spectrumDb: toFloat32Array(snapshot.spectrumDb),
    historyRow: toFloat32Array(snapshot.historyRow),
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
