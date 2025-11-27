/**
 * 导出按钮组件
 * 
 * 功能: 提供快速导出按钮（PNG、SVG、JSON）
 */

import { Download, FileJson, FileImage, Image } from 'lucide-react'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../lib/utils'

interface ExportButtonsProps {
  onExportPNG: () => void
  onExportSVG: () => void
  onExportJSON: () => void
  className?: string
}

/**
 * 导出浮动按钮组
 */
export function ExportButtons({ onExportPNG, onExportSVG, onExportJSON, className }: ExportButtonsProps) {

  const [isOpen, setIsOpen] = useState(false)

  const menuItems = [
    { label: '导出 PNG', icon: Image, action: onExportPNG },
    { label: '导出 SVG', icon: FileImage, action: onExportSVG },
    { label: '导出 JSON', icon: FileJson, action: onExportJSON },
  ]

  return (
    <div className={cn("fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3", className)}>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            className="bg-white/90 backdrop-blur-md rounded-xl shadow-xl border border-slate-200/60 p-1.5 flex flex-col gap-1 min-w-[140px]"
          >
            {menuItems.map((item, index) => (
              <motion.button
                key={item.label}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                onClick={() => {
                  item.action()
                  setIsOpen(false)
                }}
                className="flex items-center gap-3 px-3 py-2.5 text-sm text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors w-full text-left group"
              >
                <item.icon size={18} className="text-slate-400 group-hover:text-indigo-500 transition-colors" />
                <span className="font-medium">{item.label}</span>
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "w-14 h-14 rounded-full flex items-center justify-center shadow-lg shadow-indigo-500/30 transition-all duration-300",
          isOpen ? "bg-slate-800 text-white rotate-45" : "bg-indigo-600 text-white hover:bg-indigo-700"
        )}
        title="导出"
      >
        {isOpen ? <Download size={24} className="rotate-45" /> : <Download size={24} />}
      </motion.button>
    </div>
  )
}
