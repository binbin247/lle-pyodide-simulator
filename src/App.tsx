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
import type { Dispatch, SetStateAction } from 'react'
import { PlotPanel, PlotSurface } from './components/PlotPanel'
import { WaterfallCanvas } from './components/WaterfallCanvas'
import {
  DEFAULT_GRID_SIZE,
  DEFAULT_STOKES_GRID_SIZE,
  DEFAULT_STANDARD_PARAMS,
  DEFAULT_STOKES_PARAMS,
  GRID_SIZES,
} from './lib/defaults'
import { t } from './lib/i18n'
import { clampParamsForModel } from './lib/physics'
import type {
  GridSize,
  Language,
  Metrics,
  ModelId,
  SimulationParams,
  Snapshot,
  StandardParams,
  StandardSnapshot,
  StokesParams,
  StokesSnapshot,
  WorkerStatus,
  WorkerToMainMessage,
} from './types'

const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.28.3/full'
const BUSUANZI_URL = 'https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js'
const HISTORY_LIMIT = 300
const ENERGY_MIN_Y_SPAN = 0.05
const MODEL_IDS: ModelId[] = ['standard', 'stokes']

interface TracePoint {
  step: number
  energy?: number
  primaryEnergy?: number
  stokesEnergy?: number
}

interface ModelHistoryRows {
  standard: Float32Array[]
  primary: Float32Array[]
  stokes: Float32Array[]
}

interface ExportPlotSource {
  modelId: ModelId
  modelLabel: string
  snapshot: Snapshot | null
  trace: TracePoint[]
  historyRows: ModelHistoryRows
  metrics: Metrics | null
}

interface ControlDefinition {
  key: string
  min: number
  max: number
  step: number
}

interface ControlGroupDefinition {
  titleKey?: string
  controls: readonly ControlDefinition[]
}

const standardControlGroups: readonly ControlGroupDefinition[] = [
  {
    controls: [
      { key: 'alpha', min: -12, max: 20, step: 0.01 },
      { key: 'pump', min: 0, max: 8, step: 0.01 },
      { key: 'd2', min: -0.25, max: 0.25, step: 0.0001 },
      { key: 'd3', min: -0.05, max: 0.05, step: 0.0001 },
      { key: 'd4', min: -0.01, max: 0.01, step: 0.00001 },
      { key: 'tauR', min: 0, max: 0.2, step: 0.0001 },
      { key: 'dt', min: 1e-12, max: 0.005, step: 0.000001 },
      { key: 'stepsPerFrame', min: 1, max: 250, step: 1 },
    ],
  },
]

const stokesControlGroups: readonly ControlGroupDefinition[] = [
  {
    titleKey: 'primary',
    controls: [
      { key: 'alphaP', min: -20, max: 100, step: 0.01 },
      { key: 'pump', min: 0, max: 40, step: 0.01 },
      { key: 'd2P', min: -0.25, max: 0.25, step: 0.0001 },
    ],
  },
  {
    titleKey: 'stokes',
    controls: [
      { key: 'd2S', min: -0.25, max: 0.25, step: 0.0001 },
      { key: 'fsrMismatch', min: -1, max: 1, step: 0.0001 },
    ],
  },
  {
    titleKey: 'coupling',
    controls: [
      { key: 'overlap', min: 0, max: 2, step: 0.01 },
      { key: 'fR', min: 0, max: 1, step: 0.01 },
      { key: 'ramanGainP', min: 0, max: 2, step: 0.001 },
      { key: 'ramanGainS', min: 0, max: 2, step: 0.001 },
      { key: 'wavelengthRatio', min: 0.5, max: 1.5, step: 0.001 },
      { key: 'tauR', min: 0, max: 0.02, step: 0.00001 },
    ],
  },
  {
    titleKey: 'numerics',
    controls: [
      { key: 'noise', min: 0, max: 0.001, step: 0.000001 },
      { key: 'dt', min: 1e-12, max: 0.005, step: 0.000001 },
      { key: 'stepsPerFrame', min: 1, max: 10000, step: 1 },
    ],
  },
]

function App() {
  const [language, setLanguage] = useState<Language>('en')
  const labels = t(language)
  const [modelId, setModelId] = useState<ModelId>('standard')
  const [gridSizesByModel, setGridSizesByModel] = useState<Record<ModelId, GridSize>>({
    standard: DEFAULT_GRID_SIZE,
    stokes: DEFAULT_STOKES_GRID_SIZE,
  })
  const [standardParams, setStandardParams] = useState(DEFAULT_STANDARD_PARAMS)
  const [stokesParams, setStokesParams] = useState(DEFAULT_STOKES_PARAMS)
  const [status, setStatus] = useState<WorkerStatus>('idle')
  const [loadingMessage, setLoadingMessage] = useState('')
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isReady, setIsReady] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [livePreview, setLivePreview] = useState(true)
  const [trace, setTrace] = useState<TracePoint[]>([])
  const [historyRows, setHistoryRows] = useState<ModelHistoryRows>(emptyHistoryRows)
  const workerRef = useRef<Worker | null>(null)
  const modelIdRef = useRef<ModelId>('standard')
  const modelLabelRef = useRef<string>(labels.modelLabels.standard)
  const snapshotRef = useRef<Snapshot | null>(null)
  const metricsRef = useRef<Metrics | null>(null)
  const traceRef = useRef<TracePoint[]>([])
  const historyRowsRef = useRef<ModelHistoryRows>(emptyHistoryRows())
  const lastGridRef = useRef<GridSize | null>(null)
  const lastModelRef = useRef<ModelId | null>(null)
  const didInitialConfigureRef = useRef(false)
  const livePreviewRef = useRef(true)
  const isRunningRef = useRef(false)
  const previewTimerRef = useRef<number | null>(null)

  const activeParams = useMemo(
    () =>
      modelId === 'stokes'
        ? (clampParamsForModel('stokes', stokesParams) as StokesParams)
        : (clampParamsForModel('standard', standardParams) as StandardParams),
    [modelId, standardParams, stokesParams],
  )
  const gridSize = gridSizesByModel[modelId]

  const activeControlGroups =
    modelId === 'stokes' ? stokesControlGroups : standardControlGroups
  const activeHistoryRows = historyRows.standard
  const activeWaterfallCount =
    modelId === 'stokes'
      ? Math.max(historyRows.primary.length, historyRows.stokes.length)
      : historyRows.standard.length

  const intensityX = snapshot ? indexArray(getFieldLength(snapshot)) : []
  const spectrumX = snapshot ? centeredModeArray(getSpectrumLength(snapshot)) : []
  const temporalSeries = getTemporalSeries(snapshot, labels)
  const spectrumSeries = getSpectrumSeries(snapshot, labels)
  const energySeries = getEnergySeries(modelId, trace, labels)
  const stokesEnergyPanels = getStokesEnergyPanels(trace, labels)

  const resetLocalBuffers = useCallback(() => {
    const emptyRows = emptyHistoryRows()
    setSnapshot(null)
    setTrace([])
    setHistoryRows(emptyRows)
    snapshotRef.current = null
    traceRef.current = []
    historyRowsRef.current = emptyRows
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
    modelIdRef.current = modelId
    modelLabelRef.current = labels.modelLabels[modelId]
  }, [labels.modelLabels, modelId])

  useEffect(() => {
    if (document.getElementById('busuanzi-script')) {
      return
    }
    const script = document.createElement('script')
    script.id = 'busuanzi-script'
    script.async = true
    script.src = BUSUANZI_URL
    document.body.appendChild(script)
  }, [])

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
        snapshotRef.current = next
        syncClampedDt(next, setStandardParams, setStokesParams)
        setTrace((items) => {
          const clipped = [...items, tracePointFromSnapshot(next)].slice(-HISTORY_LIMIT)
          traceRef.current = clipped
          return clipped
        })
        setHistoryRows((rows) => {
          const clipped = appendHistoryRows(rows, next)
          historyRowsRef.current = clipped
          return clipped
        })
        return
      }
      if (message.type === 'metrics') {
        setMetrics(message.metrics)
        metricsRef.current = message.metrics
        return
      }
      if (message.type === 'exportState') {
        downloadJson(buildExportPayload(message.payload, {
          modelId: modelIdRef.current,
          modelLabel: modelLabelRef.current,
          snapshot: snapshotRef.current,
          trace: traceRef.current,
          historyRows: historyRowsRef.current,
          metrics: metricsRef.current,
        }))
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
    const reset =
      lastGridRef.current !== gridSize ||
      lastModelRef.current !== modelId ||
      !didInitialConfigureRef.current
    if (reset) {
      resetLocalBuffers()
      worker.postMessage({
        type: 'configure',
        modelId,
        n: gridSize,
        params: activeParams,
        reset,
      })
      lastGridRef.current = gridSize
      lastModelRef.current = modelId
      didInitialConfigureRef.current = true
    } else {
      worker.postMessage({ type: 'updateParams', modelId, params: activeParams })
      if (livePreviewRef.current && !isRunningRef.current) {
        clearPreviewTimer()
        previewTimerRef.current = window.setTimeout(() => {
          previewTimerRef.current = null
          worker.postMessage({ type: 'step' })
          setStatus('paused')
        }, 35)
      }
    }
  }, [activeParams, clearPreviewTimer, gridSize, isReady, modelId, resetLocalBuffers])

  const changeModel = (nextModelId: ModelId) => {
    if (nextModelId === modelId) {
      return
    }
    clearPreviewTimer()
    setIsRunning(false)
    setStatus(isReady ? 'ready' : 'loading')
    workerRef.current?.postMessage({ type: 'pause' })
    resetLocalBuffers()
    setModelId(nextModelId)
  }

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

  return (
    <div className="app-shell">
      <aside className="control-panel">
        <header className="app-header">
          <div>
            <h1>{labels.title}</h1>
            <p>{labels.subtitle}</p>
            <p className="usage-counter" id="busuanzi_container_site_pv">
              {labels.usageCount}
              <span id="busuanzi_value_site_pv">--</span>
            </p>
            <label className="model-selector">
              <span>{labels.model}</span>
              <select
                value={modelId}
                onChange={(event) => changeModel(event.target.value as ModelId)}
              >
                {MODEL_IDS.map((id) => (
                  <option key={id} value={id}>
                    {labels.modelLabels[id]}
                  </option>
                ))}
              </select>
            </label>
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
                onClick={() =>
                  setGridSizesByModel((current) => ({ ...current, [modelId]: size }))
                }
              >
                {size}
              </button>
            ))}
          </div>
        </section>

        <section className="panel-section">
          <div className="section-title">{labels.params}</div>
          <ControlGrid
            groups={activeControlGroups}
            labels={labels}
            values={activeParams}
            onChange={(key, value) => {
              if (modelId === 'stokes') {
                setStokesParams((current) => ({ ...current, [key]: value }) as StokesParams)
              } else {
                setStandardParams(
                  (current) => ({ ...current, [key]: value }) as StandardParams,
                )
              }
            }}
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
        </section>
      </aside>

      <main className="workspace">
        <section className="metric-strip">
          <Metric label="steps/s" value={formatNumber(metrics?.stepsPerSecond ?? 0)} />
          <Metric label="snap/s" value={formatNumber(metrics?.snapshotRate ?? 0)} />
          <Metric label="mem MB" value={formatNumber(metrics?.memoryMb ?? 0)} />
          <Metric label="batch ms" value={formatNumber(metrics?.batchMs ?? 0)} />
          <Metric label="latency ms" value={formatNumber(metrics?.latencyMs ?? 0)} />
          <Metric label="load %" value={formatNumber(metrics?.loadPercent ?? 0)} />
        </section>

        <section className="plot-grid">
          <PlotPanel
            title={labels.timeDomain}
            x={intensityX}
            series={temporalSeries}
            yTitle={labels.intensity}
            color="#2364aa"
          />
          <PlotPanel
            title={labels.spectrum}
            x={spectrumX}
            series={spectrumSeries}
            yTitle={labels.spectrumDb}
            color="#c43b42"
          />
          {modelId === 'stokes' ? (
            <section className="visual-panel energy-panel">
              <div className="visual-header">
                <h2>{labels.traces}</h2>
              </div>
              <div className="energy-pair">
                <div className="energy-subpanel">
                  <div className="energy-subheader">{labels.primary}</div>
                  <PlotSurface
                    x={trace.map((item) => item.step)}
                    series={stokesEnergyPanels.primary}
                    yTitle={labels.energy}
                    color="#287d5a"
                    yMinSpan={ENERGY_MIN_Y_SPAN}
                    yFloor={0}
                  />
                </div>
                <div className="energy-subpanel">
                  <div className="energy-subheader">{labels.stokes}</div>
                  <PlotSurface
                    x={trace.map((item) => item.step)}
                    series={stokesEnergyPanels.stokes}
                    yTitle={labels.energy}
                    color="#c43b42"
                    yMinSpan={ENERGY_MIN_Y_SPAN}
                    yFloor={0}
                  />
                </div>
              </div>
            </section>
          ) : (
            <PlotPanel
              title={labels.traces}
              x={trace.map((item) => item.step)}
              series={energySeries}
              yTitle={labels.energy}
              color="#287d5a"
              yMinSpan={ENERGY_MIN_Y_SPAN}
              yFloor={0}
            />
          )}
          <section className="visual-panel waterfall-panel">
            <div className="visual-header">
              <h2>{labels.waterfall}</h2>
              <span>{activeWaterfallCount}/{HISTORY_LIMIT}</span>
            </div>
            {modelId === 'stokes' ? (
              <div className="waterfall-pair">
                <div className="waterfall-subpanel">
                  <div className="waterfall-subheader">{labels.primary}</div>
                  <WaterfallCanvas rows={historyRows.primary} label={labels.primary} />
                </div>
                <div className="waterfall-subpanel">
                  <div className="waterfall-subheader">{labels.stokes}</div>
                  <WaterfallCanvas rows={historyRows.stokes} label={labels.stokes} />
                </div>
              </div>
            ) : (
              <WaterfallCanvas rows={activeHistoryRows} />
            )}
          </section>
        </section>

        <footer className="site-footer">
          © 2026 Binbin Nie. CyberMicrocomb. Code licensed under MIT License.
        </footer>
      </main>
    </div>
  )
}

function ControlGrid({
  groups,
  labels,
  values,
  onChange,
}: {
  groups: readonly ControlGroupDefinition[]
  labels: ReturnType<typeof t>
  values: SimulationParams
  onChange: (key: string, value: number) => void
}) {
  const valuesByKey = values as unknown as Record<string, number>
  return (
    <div className="control-groups">
      {groups.map((group, groupIndex) => (
        <div key={group.titleKey ?? groupIndex} className="control-group">
          {group.titleKey && (
            <div className="control-subtitle">
              {labels.controlGroups[group.titleKey as keyof typeof labels.controlGroups]}
            </div>
          )}
          <div className="control-grid">
            {group.controls.map(({ key, min, max, step }) => {
              const value = valuesByKey[key] ?? 0
              const help = labels.parameterHelp[key as keyof typeof labels.parameterHelp]
              const helpId = `parameter-help-${key}`
              return (
                <label key={key} className="control-row">
                  <span className="control-label">
                    <span className="control-label-text">
                      {labels.parameterLabels[key as keyof typeof labels.parameterLabels] ?? key}
                    </span>
                    {help && (
                      <span id={helpId} className="parameter-tooltip" role="tooltip">
                        {help.map((line) => (
                          <span key={line}>{line}</span>
                        ))}
                      </span>
                    )}
                  </span>
                  <input
                    type="range"
                    min={min}
                    max={max}
                    step={step}
                    value={value}
                    aria-label={
                      labels.parameterLabels[key as keyof typeof labels.parameterLabels] ?? key
                    }
                    aria-describedby={help ? helpId : undefined}
                    onChange={(event) =>
                      onChange(key, clampControlValue(Number(event.target.value), min, max))
                    }
                  />
                  <input
                    type="number"
                    min={min}
                    max={max}
                    step={step}
                    value={value}
                    aria-label={
                      labels.parameterLabels[key as keyof typeof labels.parameterLabels] ?? key
                    }
                    aria-describedby={help ? helpId : undefined}
                    onChange={(event) =>
                      onChange(key, clampControlValue(Number(event.target.value), min, max))
                    }
                  />
                </label>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

function syncClampedDt(
  snapshot: Snapshot,
  setStandardParams: Dispatch<SetStateAction<StandardParams>>,
  setStokesParams: Dispatch<SetStateAction<StokesParams>>,
) {
  if (snapshot.modelId === 'stokes') {
    setStokesParams((current) =>
      snapshot.normalizedParams.dt < current.dt - 1e-12
        ? { ...current, dt: snapshot.normalizedParams.dt }
        : current,
    )
    return
  }
  setStandardParams((current) =>
    snapshot.normalizedParams.dt < current.dt - 1e-12
      ? { ...current, dt: snapshot.normalizedParams.dt }
      : current,
  )
}

function tracePointFromSnapshot(snapshot: Snapshot): TracePoint {
  if (snapshot.modelId === 'stokes') {
    return {
      step: snapshot.step,
      primaryEnergy: snapshot.primaryEnergy,
      stokesEnergy: snapshot.stokesEnergy,
    }
  }
  return { step: snapshot.step, energy: snapshot.energy }
}

function appendHistoryRows(rows: ModelHistoryRows, snapshot: Snapshot): ModelHistoryRows {
  if (snapshot.modelId === 'stokes') {
    return {
      standard: [],
      primary: [...rows.primary, snapshot.primaryHistoryRow].slice(-HISTORY_LIMIT),
      stokes: [...rows.stokes, snapshot.stokesHistoryRow].slice(-HISTORY_LIMIT),
    }
  }
  return {
    standard: [...rows.standard, snapshot.historyRow].slice(-HISTORY_LIMIT),
    primary: [],
    stokes: [],
  }
}

function emptyHistoryRows(): ModelHistoryRows {
  return { standard: [], primary: [], stokes: [] }
}

function getFieldLength(snapshot: Snapshot) {
  return snapshot.modelId === 'stokes'
    ? snapshot.primaryIntensity.length
    : snapshot.intensity.length
}

function getSpectrumLength(snapshot: Snapshot) {
  return snapshot.modelId === 'stokes'
    ? snapshot.primarySpectrumDb.length
    : snapshot.spectrumDb.length
}

function getTemporalSeries(snapshot: Snapshot | null, labels: ReturnType<typeof t>) {
  if (!snapshot) {
    return [{ name: labels.intensity, y: [] }]
  }
  if (snapshot.modelId === 'stokes') {
    return [
      { name: `${labels.primary} |P|^2`, y: snapshot.primaryIntensity, color: '#2364aa' },
      { name: `${labels.stokes} |S|^2`, y: snapshot.stokesIntensity, color: '#c43b42' },
    ]
  }
  return [{ name: labels.intensity, y: snapshot.intensity }]
}

function getSpectrumSeries(snapshot: Snapshot | null, labels: ReturnType<typeof t>) {
  if (!snapshot) {
    return [{ name: labels.spectrumDb, y: [] }]
  }
  if (snapshot.modelId === 'stokes') {
    return [
      { name: labels.primary, y: snapshot.primarySpectrumDb, color: '#2364aa' },
      { name: labels.stokes, y: snapshot.stokesSpectrumDb, color: '#c43b42' },
    ]
  }
  return [{ name: labels.spectrumDb, y: snapshot.spectrumDb }]
}

function getEnergySeries(
  modelId: ModelId,
  trace: TracePoint[],
  labels: ReturnType<typeof t>,
) {
  if (modelId === 'stokes') {
    return [
      {
        name: labels.primary,
        y: trace.map((item) => item.primaryEnergy ?? 0),
        color: '#287d5a',
      },
      {
        name: labels.stokes,
        y: trace.map((item) => item.stokesEnergy ?? 0),
        color: '#c43b42',
      },
    ]
  }
  return [{ name: labels.energy, y: trace.map((item) => item.energy ?? 0) }]
}

function getStokesEnergyPanels(trace: TracePoint[], labels: ReturnType<typeof t>) {
  return {
    primary: [
      {
        name: labels.primary,
        y: trace.map((item) => item.primaryEnergy ?? 0),
        color: '#287d5a',
      },
    ],
    stokes: [
      {
        name: labels.stokes,
        y: trace.map((item) => item.stokesEnergy ?? 0),
        color: '#c43b42',
      },
    ],
  }
}

function isStokesSnapshot(snapshot: Snapshot | null): snapshot is StokesSnapshot {
  return snapshot?.modelId === 'stokes'
}

function isStandardSnapshot(snapshot: Snapshot | null): snapshot is StandardSnapshot {
  return snapshot?.modelId === 'standard'
}

function clampControlValue(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) {
    return min
  }
  return Math.min(max, Math.max(min, value))
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

function buildExportPayload(solverState: unknown, source: ExportPlotSource) {
  const snapshot = source.snapshot
  const solverStateObject = isObjectRecord(solverState) ? solverState : { solverState }
  const base = {
    ...solverStateObject,
    exportSchemaVersion: 3,
    exportedAt: new Date().toISOString(),
    modelId: source.modelId,
    modelLabel: source.modelLabel,
    metrics: source.metrics,
  }

  if (isStokesSnapshot(snapshot)) {
    const primaryRows = source.historyRows.primary.map((row) => Array.from(row))
    const stokesRows = source.historyRows.stokes.map((row) => Array.from(row))
    const primaryEnergy = source.trace.map((item) => item.primaryEnergy ?? 0)
    const stokesEnergy = source.trace.map((item) => item.stokesEnergy ?? 0)
    return {
      ...base,
      fields: {
        psiP_real: asNumberArray(solverStateObject.psiP_real),
        psiP_imag: asNumberArray(solverStateObject.psiP_imag),
        psiS_real: asNumberArray(solverStateObject.psiS_real),
        psiS_imag: asNumberArray(solverStateObject.psiS_imag),
      },
      currentSnapshot: {
        step: snapshot.step,
        t: snapshot.t,
        primaryEnergy: snapshot.primaryEnergy,
        stokesEnergy: snapshot.stokesEnergy,
        primaryPeak: snapshot.primaryPeak,
        stokesPeak: snapshot.stokesPeak,
        normalizedParams: snapshot.normalizedParams,
      },
      plots: {
        temporalField: {
          x: indexArray(snapshot.primaryIntensity.length),
          primaryIntensity: Array.from(snapshot.primaryIntensity),
          stokesIntensity: Array.from(snapshot.stokesIntensity),
          xLabel: 'sample index',
          yLabel: '|psi|^2',
        },
        combSpectrum: {
          mode: centeredModeArray(snapshot.primarySpectrumDb.length),
          primarySpectrumDb: Array.from(snapshot.primarySpectrumDb),
          stokesSpectrumDb: Array.from(snapshot.stokesSpectrumDb),
          xLabel: 'mode index mu',
          yLabel: 'Spectrum (dB)',
        },
        intracavityEnergy: {
          step: source.trace.map((item) => item.step),
          primary: primaryEnergy,
          stokes: stokesEnergy,
          primaryEnergy,
          stokesEnergy,
          xLabel: 'solver step',
          yLabel: 'Energy',
        },
        temporalEvolution: {
          primaryRows,
          stokesRows,
          rowCount: Math.max(primaryRows.length, stokesRows.length),
          columnCount: primaryRows[0]?.length ?? stokesRows[0]?.length ?? 0,
          valueLabel: '10 * log10(|psi|^2 + 1e-12)',
          maxRows: HISTORY_LIMIT,
        },
      },
    }
  }

  if (isStandardSnapshot(snapshot)) {
    const waterfallRows = source.historyRows.standard.map((row) => Array.from(row))
    return {
      ...base,
      currentSnapshot: {
        step: snapshot.step,
        t: snapshot.t,
        energy: snapshot.energy,
        peak: snapshot.peak,
        normalizedParams: snapshot.normalizedParams,
      },
      plots: {
        temporalField: {
          x: indexArray(snapshot.intensity.length),
          intensity: Array.from(snapshot.intensity),
          xLabel: 'sample index',
          yLabel: '|psi|^2',
        },
        combSpectrum: {
          mode: centeredModeArray(snapshot.spectrumDb.length),
          spectrumDb: Array.from(snapshot.spectrumDb),
          xLabel: 'mode index mu',
          yLabel: 'Spectrum (dB)',
        },
        intracavityEnergy: {
          step: source.trace.map((item) => item.step),
          energy: source.trace.map((item) => item.energy ?? 0),
          xLabel: 'solver step',
          yLabel: 'Energy',
        },
        temporalEvolution: {
          rows: waterfallRows,
          rowCount: waterfallRows.length,
          columnCount: waterfallRows[0]?.length ?? 0,
          valueLabel: '10 * log10(|psi|^2 + 1e-12)',
          maxRows: HISTORY_LIMIT,
        },
      },
    }
  }

  return { ...base, currentSnapshot: null, plots: null }
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function asNumberArray(value: unknown) {
  return Array.isArray(value) ? value.filter((item) => typeof item === 'number') : []
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
  anchor.download = `cybermicrocomb-state-${Date.now()}.json`
  anchor.click()
  URL.revokeObjectURL(url)
}

export default App
