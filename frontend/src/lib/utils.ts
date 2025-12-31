/**
 * 模块名称：utils
 * 主要功能：工具函数
 * 
 * 提供通用的工具函数，如 Tailwind CSS 类名合并。
 */
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * 合并 Tailwind CSS 类名
 * @param inputs - 类名列表
 * @returns 合并后的类名字符串
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
