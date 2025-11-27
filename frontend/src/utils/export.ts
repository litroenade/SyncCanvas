/**
 * 导出工具函数
 * 
 * 功能: 导出白板为 PNG、SVG、JSON
 */

import type { Stage } from 'konva/lib/Stage'
import type { WhiteboardElement } from '../types'

/**
 * 导出为 PNG 图片
 */
export function exportToPNG(stage: Stage, filename = 'whiteboard.png') {
  const uri = stage.toDataURL({ pixelRatio: 2 })
  const link = document.createElement('a')
  link.download = filename
  link.href = uri
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

/**
 * 导出为 SVG
 */
export function exportToSVG(elements: WhiteboardElement[], width: number, height: number, filename = 'whiteboard.svg') {
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">\n`
  
  elements.forEach((el) => {
    if (el.type === 'rect') {
      svg += `  <rect x="${el.x}" y="${el.y}" width="${el.width}" height="${el.height}" `
      svg += `stroke="${el.strokeColor}" stroke-width="${el.strokeWidth}" `
      svg += `fill="${el.fillColor || 'none'}" />\n`
    } else if (el.type === 'ellipse') {
      svg += `  <ellipse cx="${el.x}" cy="${el.y}" rx="${el.radiusX}" ry="${el.radiusY}" `
      svg += `stroke="${el.strokeColor}" stroke-width="${el.strokeWidth}" `
      svg += `fill="${el.fillColor || 'none'}" />\n`
    } else if (el.type === 'pen') {
      const pathData = `M ${el.points.join(' L ')}`
      svg += `  <path d="${pathData}" stroke="${el.strokeColor}" stroke-width="${el.strokeWidth}" fill="none" />\n`
    } else if (el.type === 'text') {
      svg += `  <text x="${el.x}" y="${el.y}" font-size="${el.fontSize}" fill="${el.fillColor || el.strokeColor}">${el.text}</text>\n`
    }
  })
  
  svg += '</svg>'
  
  const blob = new Blob([svg], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.download = filename
  link.href = url
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * 导出为 JSON
 */
export function exportToJSON(elements: WhiteboardElement[], filename = 'whiteboard.json') {
  const data = {
    version: '1.0',
    timestamp: new Date().toISOString(),
    elements,
  }
  
  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.download = filename
  link.href = url
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * 从 JSON 导入元素
 */
export function importFromJSON(jsonString: string): WhiteboardElement[] {
  try {
    const data = JSON.parse(jsonString)
    return data.elements || []
  } catch (error) {
    console.error('JSON 解析失败:', error)
    return []
  }
}
