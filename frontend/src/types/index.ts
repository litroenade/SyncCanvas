/**
 * 类型定义文件
 * 
 * 模块名称: types
 * 主要功能: 导出所有公共类型定义
 * 
 */

import type { LucideIcon } from 'lucide-react'

/**
 * 任务状态枚举
 */
export type TaskStatus = 'todo' | 'in_progress' | 'done'

/**
 * 任务数据接口
 */
export interface Task {
  /** 任务唯一标识 */
  id: number
  /** 任务标题 */
  title: string
  /** 任务状态 */
  status: TaskStatus
  /** 任务负责人 */
  assignee?: string
  /** 创建时间 */
  created_at?: string
  /** 更新时间 */
  updated_at?: string
}

/**
 * 绘图工具类型
 */
export type ToolType = 'select' | 'pen' | 'rect' | 'circle' | 'text' | 'note' | 'eraser' | 'arrow' | 'line'

/**
 * 工具项配置接口
 */
export interface ToolItem {
  /** 工具唯一标识 */
  id: ToolType
  /** 工具显示名称 */
  label: string
  /** 工具图标组件 */
  icon: LucideIcon
  /** 快捷键提示 */
  shortcut?: string
}

/** 工具栏图标组合 */
export interface ToolbarIconSet {
  /** 组合唯一标识 */
  id: string
  /** 组合名称 */
  name: string
  /** 组合描述 */
  description?: string
  /** 工具映射 */
  tools: Record<ToolType, ToolItem>
}

/**
 * 在线统计数据接口
 */
export interface StatsData {
  /** 在线用户数 */
  online_users: number
  /** 活跃房间数 */
  active_rooms?: number
}

/**
 * WebSocket 消息接口
 */
export interface WSMessage {
  /** 消息类型 */
  type: string
  /** 消息数据 */
  data: unknown
  /** 发送者ID */
  sender_id?: string
  /** 时间戳 */
  timestamp?: number
}

/**
 * 白板基类元素
 */
export interface WhiteboardElementBase {
  id: string
  type: 'rect' | 'ellipse' | 'pen' | 'text' | 'arrow' | 'line'
  x: number
  y: number
  rotation?: number
  strokeColor: string
  strokeWidth: number
  fillColor?: string
}

/** 矩形元素 */
export interface RectElement extends WhiteboardElementBase {
  type: 'rect'
  width: number
  height: number
}

/** 椭圆元素 */
export interface EllipseElement extends WhiteboardElementBase {
  type: 'ellipse'
  radiusX: number
  radiusY: number
}

/** 画笔元素 */
export interface PenElement extends WhiteboardElementBase {
  type: 'pen'
  points: number[]
}

/** 文本元素 */
export interface TextElement extends WhiteboardElementBase {
  type: 'text'
  text: string
  fontSize: number
}

/** 箭头元素 */
export interface ArrowElement extends WhiteboardElementBase {
  type: 'arrow'
  points: number[]
}

/** 直线元素 */
export interface LineElement extends WhiteboardElementBase {
  type: 'line'
  points: number[]
}

/** 白板元素联合类型 */
export type WhiteboardElement =
  | RectElement
  | EllipseElement
  | PenElement
  | TextElement
  | ArrowElement
  | LineElement
