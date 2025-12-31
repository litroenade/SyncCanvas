import { useState, useEffect } from 'react'
import { Users, ArrowRight } from 'lucide-react'

interface WelcomeModalProps {
  isOpen: boolean
  onJoin: (nickname: string) => void
}

export function WelcomeModal({ isOpen, onJoin }: WelcomeModalProps) {
  const [nickname, setNickname] = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    // 尝试从 localStorage 获取上次的昵称
    const savedNickname = localStorage.getItem('sync_canvas_nickname')
    if (savedNickname) {
      setNickname(savedNickname)
    }
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (nickname.trim()) {
      localStorage.setItem('sync_canvas_nickname', nickname.trim())
      onJoin(nickname.trim())
    }
  }

  if (!isOpen) return null

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-opacity duration-300 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
      {/* 背景遮罩 */}
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" />

      {/* 模态框内容 */}
      <div className="relative w-full max-w-md bg-white/90 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl overflow-hidden transform transition-all scale-100">
        <div className="p-8">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </div>
          </div>

          <h2 className="text-2xl font-bold text-center text-slate-800 mb-2">欢迎使用智能协作白板</h2>
          <p className="text-center text-slate-500 mb-8">实时捕捉灵感，与团队无缝协作</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="nickname" className="text-sm font-medium text-slate-700 block">
                你的昵称
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Users size={18} />
                </div>
                <input
                  type="text"
                  id="nickname"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-slate-50 focus:bg-white"
                  placeholder="输入你的名字..."
                  autoFocus
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={!nickname.trim()}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl transition-colors shadow-lg shadow-indigo-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>进入白板</span>
              <ArrowRight size={18} />
            </button>
          </form>
        </div>

        <div className="px-8 py-4 bg-slate-50 border-t border-slate-100 text-center">
          <p className="text-xs text-slate-400">
            基于 CRDT 技术构建 · 支持多人实时协作
          </p>
        </div>
      </div>
    </div>
  )
}
