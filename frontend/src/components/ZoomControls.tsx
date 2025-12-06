import { Minus, Plus, RotateCcw, Maximize } from 'lucide-react'
import { useCanvasStore } from '../stores/useCanvasStore'

/**
 * 缩放控制组件
 * 
 * 提供放大、缩小、重置视图和适应屏幕功能。
 * 点击百分比数字可重置为 100%。
 */
export function ZoomControls() {
  const { scale, setScale, setOffset, shapes } = useCanvasStore()

  const handleZoomIn = () => {
    setScale(Math.min(scale * 1.2, 10))
  }

  const handleZoomOut = () => {
    setScale(Math.max(scale / 1.2, 0.1))
  }

  const handleResetScale = () => {
    setScale(1)
  }

  const handleReset = () => {
    setScale(1)
    setOffset({ x: 0, y: 0 })
  }

  const handleFitToContent = () => {
    const elements = Object.values(shapes)
    if (elements.length === 0) {
      handleReset()
      return
    }

    let minX = Infinity
    let minY = Infinity
    let maxX = -Infinity
    let maxY = -Infinity

    elements.forEach(el => {
      const width = el.width || 100
      const height = el.height || 100

      minX = Math.min(minX, el.x)
      maxX = Math.max(maxX, el.x + width)
      minY = Math.min(minY, el.y)
      maxY = Math.max(maxY, el.y + height)
    })

    if (minX === Infinity) {
      handleReset()
      return
    }

    const width = maxX - minX
    const height = maxY - minY
    const padding = 50

    const stageWidth = window.innerWidth
    const stageHeight = window.innerHeight

    const safeWidth = Math.max(width, 1)
    const safeHeight = Math.max(height, 1)

    const scaleX = (stageWidth - padding * 2) / safeWidth
    const scaleY = (stageHeight - padding * 2) / safeHeight
    const newScale = Math.min(scaleX, scaleY, 1)

    const contentCenterX = minX + width / 2
    const contentCenterY = minY + height / 2

    const newOffsetX = (stageWidth / 2) - (contentCenterX * newScale)
    const newOffsetY = (stageHeight / 2) - (contentCenterY * newScale)

    setScale(newScale)
    setOffset({ x: newOffsetX, y: newOffsetY })
  }

  return (
    <div className="flex items-center gap-1 p-1 bg-white/90 backdrop-blur-md rounded-lg shadow-sm border border-slate-200/60 pointer-events-auto">
      <button
        onClick={handleZoomOut}
        className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
        title="缩小"
      >
        <Minus size={16} />
      </button>
      <button
        onClick={handleResetScale}
        className="w-12 text-center text-xs font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 py-1 rounded-md transition-colors"
        title="点击重置为 100%"
      >
        {Math.round(scale * 100)}%
      </button>
      <button
        onClick={handleZoomIn}
        className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
        title="放大"
      >
        <Plus size={16} />
      </button>

      <div className="w-px h-4 bg-slate-200 mx-1" />

      <button
        onClick={handleFitToContent}
        className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
        title="适应屏幕"
      >
        <Maximize size={16} />
      </button>
      <button
        onClick={handleReset}
        className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
        title="重置视图"
      >
        <RotateCcw size={16} />
      </button>
    </div>
  )
}

