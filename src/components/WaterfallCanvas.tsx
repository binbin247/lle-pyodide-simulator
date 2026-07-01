import { useEffect, useRef } from 'react'

export function WaterfallCanvas({ rows }: { rows: Float32Array[] }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) {
      return
    }
    const width = rows[0]?.length ?? 512
    const height = Math.max(1, rows.length || 1)
    canvas.width = width
    canvas.height = Math.max(128, height)
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      return
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    if (rows.length === 0) {
      ctx.fillStyle = '#f4f6f8'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      return
    }

    let min = Infinity
    let max = -Infinity
    for (const row of rows) {
      for (let i = 0; i < row.length; i += 1) {
        const value = row[i]
        if (Number.isFinite(value)) {
          min = Math.min(min, value)
          max = Math.max(max, value)
        }
      }
    }
    if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
      min = -80
      max = 0
    }

    const image = ctx.createImageData(width, height)
    const offsetY = height - rows.length
    rows.forEach((row, rowIndex) => {
      const y = offsetY + rowIndex
      for (let x = 0; x < width; x += 1) {
        const value = row[x] ?? min
        const [r, g, b] = colorMap((value - min) / (max - min))
        const idx = (y * width + x) * 4
        image.data[idx] = r
        image.data[idx + 1] = g
        image.data[idx + 2] = b
        image.data[idx + 3] = 255
      }
    })
    ctx.putImageData(image, 0, 0)
  }, [rows])

  return <canvas ref={canvasRef} className="waterfall-canvas" aria-label="waterfall" />
}

function colorMap(input: number): [number, number, number] {
  const v = Math.max(0, Math.min(1, input))
  const stops: Array<[number, number, number, number]> = [
    [0, 24, 30, 78],
    [0.28, 32, 100, 170],
    [0.55, 35, 160, 140],
    [0.78, 244, 166, 66],
    [1, 245, 238, 160],
  ]
  for (let i = 1; i < stops.length; i += 1) {
    const prev = stops[i - 1]
    const next = stops[i]
    if (v <= next[0]) {
      const local = (v - prev[0]) / (next[0] - prev[0])
      return [
        Math.round(prev[1] + (next[1] - prev[1]) * local),
        Math.round(prev[2] + (next[2] - prev[2]) * local),
        Math.round(prev[3] + (next[3] - prev[3]) * local),
      ]
    }
  }
  return [245, 238, 160]
}
