import {
  MousePointer2,
  Pointer,
  PencilLine,
  Paintbrush,
  Square,
  Frame,
  Circle,
  Disc,
  Type,
  Heading,
  StickyNote,
  BookOpen,
  Eraser,
  ArrowRight,
  Minus,
} from 'lucide-react'
import type { ToolbarIconSet } from '../types'

export const toolbarIconSets: ToolbarIconSet[] = [
  {
    id: 'classic',
    name: '经典图标',
    description: 'Lucide 线条风格，便于识别',
    tools: {
      select: { id: 'select', label: '选择', icon: MousePointer2, shortcut: 'V' },
      pen: { id: 'pen', label: '画笔', icon: PencilLine, shortcut: 'B' },
      rect: { id: 'rect', label: '矩形', icon: Square, shortcut: 'R' },
      circle: { id: 'circle', label: '椭圆', icon: Circle, shortcut: 'O' },
      arrow: { id: 'arrow', label: '箭头', icon: ArrowRight, shortcut: 'A' },
      line: { id: 'line', label: '直线', icon: Minus, shortcut: 'L' },
      text: { id: 'text', label: '文本', icon: Type, shortcut: 'T' },
      note: { id: 'note', label: '便签', icon: StickyNote, shortcut: 'N' },
      eraser: { id: 'eraser', label: '橡皮擦', icon: Eraser, shortcut: 'E' },
    },
  },
  {
    id: 'minimal',
    name: '极简图标',
    description: '细线配虚线风格，适合暗色主题',
    tools: {
      select: { id: 'select', label: '选择', icon: Pointer, shortcut: 'V' },
      pen: { id: 'pen', label: '画笔', icon: Paintbrush, shortcut: 'B' },
      rect: { id: 'rect', label: '矩形', icon: Frame, shortcut: 'R' },
      circle: { id: 'circle', label: '椭圆', icon: Disc, shortcut: 'O' },
      arrow: { id: 'arrow', label: '箭头', icon: ArrowRight, shortcut: 'A' },
      line: { id: 'line', label: '直线', icon: Minus, shortcut: 'L' },
      text: { id: 'text', label: '文本', icon: Heading, shortcut: 'T' },
      note: { id: 'note', label: '便签', icon: BookOpen, shortcut: 'N' },
      eraser: { id: 'eraser', label: '橡皮擦', icon: Eraser, shortcut: 'E' },
    },
  },
]
