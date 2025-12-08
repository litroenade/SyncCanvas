import { useState } from 'react'
import { X, Sparkles, Loader2 } from 'lucide-react'
import { aiApi } from '../../services/api/ai'
import { cn } from '../../lib/utils'
import { yjsManager } from '../../lib/yjs'

interface AIGenerateModalProps {
  isOpen: boolean
  onClose: () => void
}

/**
 * AI 生成模态框
 * 
 * 提供用户输入提示词并调用 AI 生成图形的界面。
 */
export function AIGenerateModal({ isOpen, onClose }: AIGenerateModalProps) {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) return

    setLoading(true)
    setError(null)

    try {
      const roomId = yjsManager.roomId
      if (!roomId) {
        setError('未连接到房间')
        return
      }
      await aiApi.generateShapes(prompt, roomId)
      onClose()
      setPrompt('')
    } catch (err) {
      console.error(err)
      setError('生成失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white/90 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl p-6 m-4 animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2 text-indigo-600">
            <Sparkles size={24} />
            <h2 className="text-xl font-bold">AI 智能绘图</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              描述你想画的内容
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="例如：画一个登录页面的线框图，包含用户名、密码输入框和登录按钮..."
              className="w-full h-32 px-4 py-3 text-slate-700 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white resize-none transition-all"
              disabled={loading}
            />
          </div>

          {error && (
            <div className="p-3 bg-rose-50 text-rose-600 text-sm rounded-lg flex items-center gap-2">
              <X size={14} />
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors font-medium"
              disabled={loading}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className={cn(
                "flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium transition-all shadow-lg shadow-indigo-500/30",
                loading ? "opacity-70 cursor-not-allowed" : "hover:bg-indigo-700 hover:scale-105 active:scale-95",
                !prompt.trim() && "opacity-50 cursor-not-allowed hover:bg-indigo-600 hover:scale-100"
              )}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  正在生成...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  开始生成
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

