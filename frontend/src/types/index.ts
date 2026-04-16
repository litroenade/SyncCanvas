import type { LucideIcon } from 'lucide-react';

export type TaskStatus = 'todo' | 'in_progress' | 'done';

export interface Task {
  id: number;
  title: string;
  status: TaskStatus;
  assignee?: string;
  created_at?: string;
  updated_at?: string;
}

export type ToolType =
  | 'select'
  | 'pen'
  | 'rect'
  | 'circle'
  | 'text'
  | 'note'
  | 'eraser'
  | 'arrow'
  | 'line';

export interface ToolItem {
  id: ToolType;
  label: string;
  icon: LucideIcon;
  shortcut?: string;
}

export interface ToolbarIconSet {
  id: string;
  name: string;
  description?: string;
  tools: Record<ToolType, ToolItem>;
}

export interface StatsData {
  online_users: number;
  active_rooms?: number;
}

export interface WSMessage {
  type: string;
  data: unknown;
  sender_id?: string;
  timestamp?: number;
}

export type CollabEventType = 'add' | 'delete' | 'update';

export interface CollabEvent {
  id: string;
  ts: number;
  actorId: string;
  actorName: string;
  type: CollabEventType;
  elementType: string;
  summary: string;
  isMe: boolean;
}

export interface WhiteboardElementBase {
  id: string;
  type: 'rect' | 'ellipse' | 'pen' | 'text' | 'arrow' | 'line';
  x: number;
  y: number;
  rotation?: number;
  strokeColor: string;
  strokeWidth: number;
  fillColor?: string;
}

export interface RectElement extends WhiteboardElementBase {
  type: 'rect';
  width: number;
  height: number;
}

export interface EllipseElement extends WhiteboardElementBase {
  type: 'ellipse';
  radiusX: number;
  radiusY: number;
}

export interface PenElement extends WhiteboardElementBase {
  type: 'pen';
  points: number[];
}

export interface TextElement extends WhiteboardElementBase {
  type: 'text';
  text: string;
  fontSize: number;
}

export interface ArrowElement extends WhiteboardElementBase {
  type: 'arrow';
  points: number[];
}

export interface LineElement extends WhiteboardElementBase {
  type: 'line';
  points: number[];
}

export type WhiteboardElement =
  | RectElement
  | EllipseElement
  | PenElement
  | TextElement
  | ArrowElement
  | LineElement;

export * from './diagram';
