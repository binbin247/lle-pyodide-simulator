import {
  Activity,
  Download,
  Languages,
  Pause,
  Play,
  RotateCcw,
  StepForward,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { PlotPanel } from './components/PlotPanel'
import { WaterfallCanvas } from './components/WaterfallCanvas'
import {
  DEFAULT_GRID_SIZE,
  DEFAULT_NORMALIZED_PARAMS,
  GRID_SIZES,
} from './lib/defaults'
import { t } from './lib/i18n'
import { clampNormalizedParams } from './lib/physics'
import type {
  GridSize,
  Language,
  Metrics,
  NormalizedParams,
  Snapshot,
  WorkerStatus,
  WorkerToMainMessage,
} from './types'

const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.28.3/full'
const HISTORY_LIMIT = 300

const normalizedControls = [
  ['alpha', -12, 20, 0.01, 'alphaTip'],
  ['pump', 0, 8, 0.01, 'pumpTip'],
  ['d2', -0.25, 0.25, 0.0001, 'd2Tip'],
  ['d3', -0.05, 0.05, 0.0001, 'd3Tip'],
  ['d4', -0.01, 0.01, 0.00001, 'd4Tip'],
  ['tauR', 0, 0.2, 0.0001, 'tauTip'],
  ['dt', 0.00001, 0.005, 0.00001, 'dtTip'],
  ['stepsPerFrame', 1, 250, 1, 'stepsTip'],
] as const

function App() {
  const [language, setLanguage] = useState<Language>('en')
  const labels = t(language)
  const [gridSize, setGridSize] = useState<GridSize>(DEFAULT_GRID_SIZE)
  const [normalized, setNormalized] = useState(DEFAULT_NORMALIZED_PARAMS)
  const [status, setStatus] = useState<WorkerStatus>('idle')
  const [loadingMessage, setLoadingMessage] = useState('')
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isReady, setIsReady] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [livePreview, setLivePreview] = useState(true)
  const [trace, setTrace] = useState<Array<{ step: number; energy: number; peak: number }>>([])
  const [historyRows, setHistoryRows] = useState<Float32Array[]>([])
  const workerRef = useRef<Worker | null>(null)
  const lastGridRef = useRef<GridSize | null>(null)
  const didInitialConfigureRef = useRef(false)
  const livePreviewRef = useRef(true)
  const isRunningRef = useRef(false)
  const previewTimerRef = useRef<number | null>(null)

  const activeParams = useMemo(
    () => clampNormalizedParams(normalized),
    [normalized],
  )

  const resetLocalBuffers = useCallback(() => {
    setSnapshot(null)
    setTrace([])
    setHistoryRows([])
  }, [])

  const clearPreviewTimer = useCallback(() => {
    if (previewTimerRef.current !== null) {
      window.clearTimeout(previewTimerRef.current)
      previewTimerRef.current = null
    }
  }, [])

  useEffect(() => {
    livePreviewRef.current = livePreview
  }, [livePreview])

  useEffect(() => {
    isRunningRef.current = isRunning
  }, [isRunning])

  useEffect(() => {
    const worker = new Worker(new URL('./worker/lle.worker.ts', import.meta.url), {
      type: 'module',
    })
    workerRef.current = worker
    setStatus('loading')
    setError(null)
    const solverUrl = new URL(
      `${import.meta.env.BASE_URL}lle_solver.py`,
      window.location.origin,
    ).href

    worker.onerror = (event) => {
      setError(event.message)
      setStatus('error')
      setIsRunning(false)
    }

    worker.onmessage = (event: MessageEvent<WorkerToMainMessage>) => {
      const message = event.data
      if (message.type === 'loading') {
        setLoadingMessage(message.message)
        setError(null)
        return
      }
      if (message.type === 'ready') {
        setIsReady(true)
        setStatus('ready')
        setError(null)
        return
      }
      if (message.type === 'snapshot') {
        const next = message.snapshot
        setError(null)
        setSnapshot(next)
        setTrace((items) => {
          const updated = [
            ...items,
            { step: next.step, energy: next.energy, peak: next.peak },
          ]
          return updated.slice(-HISTORY_LIMIT)
        })
        setHistoryRows((rows) => [...rows, next.historyRow].slice(-HISTORY_LIMIT))
        return
      }
      if (message.type === 'metrics') {
        setMetrics(message.metrics)
        return
      }
      if (message.type === 'exportState') {
        downloadJson(message.payload)
        return
      }
      if (message.type === 'error') {
        setError(message.error)
        setStatus('error')
        setIsRunning(false)
      }
    }

    worker.postMessage({ type: 'init', pyodideUrl: PYODIDE_URL, solverUrl })

    return () => {
      clearPreviewTimer()
      worker.terminate()
      workerRef.current = null
    }
  }, [clearPreviewTimer])

  useEffect(() => {
    const worker = workerRef.current
    if (!worker || !isReady) {
      return
    }
    const reset = lastGridRef.current !== gridSize || !didInitialConfigureRef.current
    if (reset) {
      resetLocalBuffers()
      worker.postMessage({ type: 'configure', n: gridSize, params: activeParams, reset })
      lastGridRef.current = gridSize
      didInitialConfigureRef.current = true
    } else {
      worker.postMessage({ type: 'updateParams', params: activeParams })
      if (livePreviewRef.current && !isRunningRef.current) {
        clearPreviewTimer()
        previewTimerRef.current = window.setTimeout(() => {
          previewTimerRef.current = null
          worker.postMessage({ type: 'step' })
          setStatus('paused')
        }, 35)
      }
    }
  }, [activeParams, clearPreviewTimer, gridSize, isReady, resetLocalBuffers])

  const start = () => {
    if (!isReady) {
      return
    }
    clearPreviewTimer()
    setError(null)
    setIsRunning(true)
    setStatus('running')
    workerRef.current?.postMessage({ type: 'start' })
  }

  const pause = () => {
    setIsRunning(false)
    setStatus('paused')
    workerRef.current?.postMessage({ type: 'pause' })
  }

  const step = () => {
    setIsRunning(false)
    setStatus('paused')
    workerRef.current?.postMessage({ type: 'step' })
  }

  const reset = () => {
    clearPreviewTimer()
    setIsRunning(false)
    setStatus(isReady ? 'ready' : 'loading')
    resetLocalBuffers()
    workerRef.current?.postMessage({ type: 'reset' })
  }

  const exportState = () => workerRef.current?.postMessage({ type: 'exportState' })

  const modeParams = normalized
  const intensityX = snapshot ? indexArray(snapshot.intensity.length) : []
  const spectrumX = snapshot ? centeredModeArray(snapshot.spectrumDb.length) : []

  return (
    <div className="app-shell">
      <aside className="control-panel">
        <header className="app-header">
          <div>
            <h1>{labels.title}</h1>
            <p>{labels.subtitle}</p>
          </div>
          <button
            type="button"
            className="icon-button"
            title={labels.language}
            onClick={() => setLanguage((value) => (value === 'en' ? 'zh' : 'en'))}
          >
            <Languages size={18} />
            <span>{language === 'en' ? '中文' : 'EN'}</span>
          </button>
        </header>

        <section className="panel-section">
          <div className="section-title">{labels.grid}</div>
          <div className="grid-size-list">
            {GRID_SIZES.map((size) => (
              <button
                key={size}
                type="button"
                className={gridSize === size ? 'active' : ''}
                onClick={() => setGridSize(size)}
              >
                {size}
              </button>
            ))}
          </div>
        </section>

        <section className="panel-section">
          <div className="section-title">{labels.params}</div>
          <ControlGrid
            controls={normalizedControls}
            labels={labels}
            displayLabels={labels.parameterLabels}
            values={normalized}
            onChange={(key, value) =>
              setNormalized(
                (current) => ({ ...current, [key]: value }) as NormalizedParams,
              )
            }
          />
        </section>

        <section className="panel-section">
          <label className="toggle-control">
            <input
              type="checkbox"
              checked={livePreview}
              onChange={(event) => setLivePreview(event.target.checked)}
            />
            <span>{labels.livePreview}</span>
          </label>
          <div className="transport">
            <button type="button" onClick={isRunning ? pause : start} disabled={!isReady}>
              {isRunning ? <Pause size={18} /> : <Play size={18} />}
              <span>{isRunning ? labels.pause : labels.play}</span>
            </button>
            <button type="button" onClick={step} disabled={!isReady || isRunning}>
              <StepForward size={18} />
              <span>{labels.step}</span>
            </button>
            <button type="button" onClick={reset} disabled={!isReady}>
              <RotateCcw size={18} />
              <span>{labels.reset}</span>
            </button>
            <button type="button" onClick={exportState} disabled={!snapshot}>
              <Download size={18} />
              <span>{labels.export}</span>
            </button>
          </div>
        </section>

        <section className="panel-section status-section">
          <div className={`status-pill ${status}`}>
            <Activity size={16} />
            <span>{statusText(labels, status, loadingMessage)}</span>
          </div>
          {error && <p className="error-text">{error}</p>}
          <p className="method-note">{labels.warning}</p>
        </section>
      </aside>

      <main className="workspace">
        <section className="metric-strip">
          <Metric label="step" value={snapshot?.step ?? 0} />
          <Metric label="t" value={formatNumber(snapshot?.t ?? 0)} />
          <Metric label="N" value={gridSize} />
          <Metric label="steps/s" value={formatNumber(metrics?.stepsPerSecond ?? 0)} />
          <Metric label="snap/s" value={formatNumber(metrics?.snapshotRate ?? 0)} />
          <Metric label="mem MB" value={formatNumber(metrics?.memoryMb ?? 0)} />
        </section>

        <section className="plot-grid">
          <PlotPanel
            title={labels.timeDomain}
            x={intensityX}
            series={[{ name: labels.intensity, y: snapshot?.intensity ?? [] }]}
            yTitle={labels.intensity}
            color="#2364aa"
          />
          <PlotPanel
            title={labels.spectrum}
            x={spectrumX}
            series={[{ name: labels.spectrumDb, y: snapshot?.spectrumDb ?? [] }]}
            yTitle={labels.spectrumDb}
            color="#c43b42"
          />
          <PlotPanel
            title={labels.traces}
            x={trace.map((item) => item.step)}
            series={[
              { name: labels.energy, y: trace.map((item) => item.energy) },
              { name: labels.peak, y: trace.map((item) => item.peak) },
            ]}
            yTitle={labels.energy}
            color="#287d5a"
          />
          <section className="visual-panel waterfall-panel">
            <div className="visual-header">
              <h2>{labels.waterfall}</h2>
              <span>{historyRows.length}/{HISTORY_LIMIT}</span>
            </div>
            <WaterfallCanvas rows={historyRows} />
          </section>
        </section>

        <section className="model-readout">
          <div>
            <strong>{labels.parameterLabels.alpha}</strong>
            <span>{formatNumber(modeParams.alpha)}</span>
          </div>
          <div>
            <strong>{labels.parameterLabels.pump}</strong>
            <span>{formatNumber(modeParams.pump)}</span>
          </div>
          <div>
            <strong>{labels.parameterLabels.d2}</strong>
            <span>{formatNumber(modeParams.d2)}</span>
          </div>
          <div>
            <strong>{labels.parameterLabels.d3}</strong>
            <span>{formatNumber(modeParams.d3)}</span>
          </div>
          <div>
            <strong>{labels.parameterLabels.d4}</strong>
            <span>{formatNumber(modeParams.d4)}</span>
          </div>
          <div>
            <strong>tauR</strong>
            <span>{formatNumber(modeParams.tauR)}</span>
          </div>
        </section>
      </main>
    </div>
  )
}

function ControlGrid({
  controls,
  labels,
  displayLabels,
  values,
  onChange,
}: {
  controls: readonly (readonly [string, number, number, number, string?])[]
  labels: ReturnType<typeof t>
  displayLabels: Partial<Record<string, string>>
  values: NormalizedParams
  onChange: (key: string, value: number) => void
}) {
  const valuesByKey = values as unknown as Record<string, number>
  return (
    <div className="control-grid">
      {controls.map(([key, min, max, step, tipKey]) => {
        const value = valuesByKey[key] ?? 0
        const tooltip = tipKey ? labels[tipKey as keyof typeof labels] : undefined
        return (
          <label key={key} title={typeof tooltip === 'string' ? tooltip : undefined}>
            <span>{displayLabels[key] ?? key}</span>
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={value}
              onChange={(event) => onChange(key, Number(event.target.value))}
            />
            <input
              type="number"
              step={step}
              value={value}
              onChange={(event) => onChange(key, Number(event.target.value))}
            />
          </label>
        )
      })}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function statusText(
  labels: ReturnType<typeof t>,
  status: WorkerStatus,
  loadingMessage: string,
) {
  if (status === 'loading') {
    return loadingMessage || labels.loading
  }
  if (status === 'ready') {
    return labels.ready
  }
  if (status === 'running') {
    return labels.running
  }
  if (status === 'paused') {
    return labels.paused
  }
  if (status === 'error') {
    return labels.error
  }
  return status
}

function indexArray(length: number) {
  return Array.from({ length }, (_, index) => index)
}

function centeredModeArray(length: number) {
  const half = Math.floor(length / 2)
  return Array.from({ length }, (_, index) => index - half)
}

function formatNumber(value: number) {
  if (!Number.isFinite(value)) {
    return '0'
  }
  if (Math.abs(value) >= 1e4 || (Math.abs(value) > 0 && Math.abs(value) < 1e-3)) {
    return value.toExponential(2)
  }
  return value.toLocaleString(undefined, { maximumSignificantDigits: 4 })
}

function downloadJson(payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `lle-state-${Date.now()}.json`
  anchor.click()
  URL.revokeObjectURL(url)
}

export default App
