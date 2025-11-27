import getStroke from 'perfect-freehand'

export interface PenStrokeOptions {
  size?: number
  thinning?: number
  smoothing?: number
  streamline?: number
  simulatePressure?: boolean
}

/**
 * Convert point array to perfect-freehand stroke outline
 */
export function getSmoothStroke(
  points: number[],
  options: PenStrokeOptions = {}
): number[][] {
  const {
    size = 8,
    thinning = 0.5,
    smoothing = 0.5,
    streamline = 0.5,
    simulatePressure = true,
  } = options

  // Convert flat array [x1, y1, x2, y2, ...] to [[x1, y1], [x2, y2], ...]
  const pointPairs: [number, number][] = []
  for (let i = 0; i < points.length; i += 2) {
    if (i + 1 < points.length) {
      pointPairs.push([points[i], points[i + 1]])
    }
  }

  if (pointPairs.length === 0) {
    return []
  }

  const stroke = getStroke(pointPairs, {
    size,
    thinning,
    smoothing,
    streamline,
    simulatePressure,
  })

  return stroke
}

/**
 * Convert stroke outline to SVG path data
 */
export function strokeToPathData(stroke: number[][]): string {
  if (stroke.length === 0) {
    return ''
  }

  const [first, ...rest] = stroke
  let path = `M ${first[0]} ${first[1]}`

  for (const [x, y] of rest) {
    path += ` L ${x} ${y}`
  }

  path += ' Z'
  return path
}

/**
 * Flatten stroke outline to Konva-compatible points array
 */
export function strokeToFlatPoints(stroke: number[][]): number[] {
  const flat: number[] = []
  for (const [x, y] of stroke) {
    flat.push(x, y)
  }
  return flat
}
