import { create } from 'zustand'

/**
 * 工具类型
 */
export type ToolType = 'select' | 'hand' | 'rect' | 'circle' | 'diamond' | 'arrow' | 'line' | 'freedraw' | 'text' | 'image' | 'eraser'

/**
 * 图形对象接口
 */
export interface Shape {
  /** 唯一标识符 (UUID) */
  id: string
  /** 图形类型: 矩形、圆形、菱形、文本、箭头、线条、图片、自由绘制 */
  type: 'rect' | 'circle' | 'diamond' | 'text' | 'arrow' | 'line' | 'image' | 'freedraw'
  /** 世界坐标 X */
  x: number
  /** 世界坐标 Y */
  y: number
  /** 宽度 */
  width?: number
  /** 高度 */
  height?: number
  /** 填充颜色 */
  fill?: string
  /** 文本内容 (仅 type='text' 有效) */
  text?: string
  /** 图片 URL (仅 type='image' 有效) */
  imageUrl?: string
  /** 描边颜色 */
  strokeColor?: string
  /** 描边宽度 */
  strokeWidth?: number
  /** 层级 (Z-Index) */
  zIndex?: number
  /** 旋转角度 */
  rotation?: number
  /** 点集 (用于线条、箭头、自由绘制) */
  points?: number[]
  /** 透明度 */
  opacity?: number
  /** 圆角半径 */
  cornerRadius?: number
}

/**
 * 画布状态接口
 */
interface CanvasState {
  /** 当前选中的工具 */
  currentTool: ToolType
  /** 设置当前工具 */
  setCurrentTool: (tool: ToolType) => void
  /** 视图缩放比例 */
  scale: number
  /** 视图偏移量 */
  offset: { x: number; y: number }
  /** 所有图形数据 (ID -> Shape) */
  shapes: Record<string, Shape>
  /** 当前选中的图形 ID 集合 (支持多选) */
  selectedIds: string[]
  /** 是否显示网格 */
  showGrid: boolean
  /** 当前填充颜色 */
  currentFillColor: string
  /** 当前描边颜色 */
  currentStrokeColor: string
  /** 当前描边宽度 */
  currentStrokeWidth: number
  /** 设置当前填充颜色 */
  setCurrentFillColor: (color: string) => void
  /** 设置当前描边颜色 */
  setCurrentStrokeColor: (color: string) => void
  /** 设置当前描边宽度 */
  setCurrentStrokeWidth: (width: number) => void
  /** 设置网格显示状态 */
  setShowGrid: (show: boolean) => void
  /** 切换网格显示状态 */
  toggleGrid: () => void
  /** 设置缩放比例 */
  setScale: (scale: number) => void
  /** 设置偏移量 */
  setOffset: (offset: { x: number; y: number }) => void
  /** 设置所有图形 */
  setShapes: (shapes: Record<string, Shape>) => void
  /** 添加单个图形 */
  addShape: (shape: Shape) => void
  /** 更新图形属性 */
  updateShape: (id: string, attrs: Partial<Shape>) => void
  /** 删除图形 */
  deleteShape: (id: string) => void
  /** 设置选中图形 ID (单选) */
  setSelectedId: (id: string | null) => void
  /** 切换选中状态 (多选) */
  toggleSelection: (id: string) => void
  /** 远程光标数据 (ClientID -> Cursor Data) */
  cursors: Record<string, { x: number; y: number; color: string; name: string }>
  /** 设置远程光标 */
  setCursors: (cursors: Record<string, any>) => void
  /** 清除所有选中 */
  clearSelection: () => void
  /** 是否为游客模式 */
  isGuest: boolean
  /** 设置游客模式 */
  setIsGuest: (isGuest: boolean) => void
  /** 是否正在绘制 */
  isDrawing: boolean
  /** 设置绘制状态 */
  setIsDrawing: (isDrawing: boolean) => void
  /** 当前绘制的图形 ID */
  drawingShapeId: string | null
  /** 设置绘制中的图形 ID */
  setDrawingShapeId: (id: string | null) => void
}

/**
 * 画布状态管理 Hook (Zustand)
 */
export const useCanvasStore = create<CanvasState>((set) => ({
  currentTool: 'select',
  setCurrentTool: (tool) => set({ currentTool: tool }),
  scale: 1,
  offset: { x: 0, y: 0 },
  shapes: {},
  selectedIds: [], 
  showGrid: true,
  currentFillColor: 'transparent',
  currentStrokeColor: '#1e1e1e',
  currentStrokeWidth: 2,
  setCurrentFillColor: (color) => set({ currentFillColor: color }),
  setCurrentStrokeColor: (color) => set({ currentStrokeColor: color }),
  setCurrentStrokeWidth: (width) => set({ currentStrokeWidth: width }),
  setShowGrid: (show) => set({ showGrid: show }),
  toggleGrid: () => set((state) => ({ showGrid: !state.showGrid })),
  setScale: (scale) => set({ scale: Math.max(0.1, Math.min(5, scale)) }),
  setOffset: (offset) => set({ offset }),
  setShapes: (shapes) => set({ shapes }),
  setSelectedId: (id) => set({ selectedIds: id ? [id] : [] }),
  toggleSelection: (id) => set((state) => {
    const ids = new Set(state.selectedIds);
    if (ids.has(id)) {
      ids.delete(id);
    } else {
      ids.add(id);
    }
    return { selectedIds: Array.from(ids) };
  }),
  clearSelection: () => set({ selectedIds: [] }),
  cursors: {},
  setCursors: (cursors) => set({ cursors }),
  addShape: (shape) => set((state) => ({ shapes: { ...state.shapes, [shape.id]: shape } })),
  updateShape: (id, attrs) => set((state) => ({
    shapes: state.shapes[id] ? {
      ...state.shapes,
      [id]: { ...state.shapes[id], ...attrs }
    } : state.shapes
  })),
  deleteShape: (id) => set((state) => {
    const { [id]: _, ...rest } = state.shapes;
    return { shapes: rest };
  }),
  isGuest: localStorage.getItem('isGuest') === 'true',
  setIsGuest: (isGuest) => set({ isGuest }),
  isDrawing: false,
  setIsDrawing: (isDrawing) => set({ isDrawing }),
  drawingShapeId: null,
  setDrawingShapeId: (id) => set({ drawingShapeId: id }),
}))

