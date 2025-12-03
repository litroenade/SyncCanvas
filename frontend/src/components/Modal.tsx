/**
 * 模块名称: Modal
 * 主要功能: 自定义模态弹窗组件
 */

import React, { useEffect, useCallback } from 'react'
import { X, AlertTriangle, Info, CheckCircle, AlertCircle } from 'lucide-react'
import { cn } from '../lib/utils'
import { useThemeStore } from '../stores/useThemeStore'

// ==================== 基础 Modal ====================

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
  title?: string
  showCloseButton?: boolean
  closeOnOverlayClick?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  children,
  title,
  showCloseButton = true,
  closeOnOverlayClick = true,
  size = 'md',
}) => {
  const { theme } = useThemeStore()

  // ESC 键关闭
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEsc)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleEsc)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 遮罩层 */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={closeOnOverlayClick ? onClose : undefined}
      />

      {/* 弹窗内容 */}
      <div
        className={cn(
          'relative w-full mx-4 rounded-xl shadow-2xl transform transition-all',
          sizeClasses[size],
          theme === 'dark' ? 'bg-slate-800' : 'bg-white'
        )}
      >
        {/* 标题栏 */}
        {(title || showCloseButton) && (
          <div
            className={cn(
              'flex items-center justify-between px-4 py-3 border-b',
              theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
            )}
          >
            {title && (
              <h3 className={cn('font-semibold', theme === 'dark' ? 'text-slate-100' : 'text-slate-800')}>
                {title}
              </h3>
            )}
            {showCloseButton && (
              <button
                onClick={onClose}
                className={cn(
                  'p-1 rounded-lg transition-colors',
                  theme === 'dark' ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-100 text-slate-500'
                )}
              >
                <X size={18} />
              </button>
            )}
          </div>
        )}

        {/* 内容 */}
        {children}
      </div>
    </div>
  )
}

// ==================== Alert Dialog ====================

type AlertType = 'info' | 'success' | 'warning' | 'error'

interface AlertDialogProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  message: string
  type?: AlertType
  confirmText?: string
}

export const AlertDialog: React.FC<AlertDialogProps> = ({
  isOpen,
  onClose,
  title,
  message,
  type = 'info',
  confirmText = '确定',
}) => {
  const { theme } = useThemeStore()

  const icons = {
    info: <Info className="text-blue-500" size={24} />,
    success: <CheckCircle className="text-green-500" size={24} />,
    warning: <AlertTriangle className="text-amber-500" size={24} />,
    error: <AlertCircle className="text-red-500" size={24} />,
  }

  const buttonColors = {
    info: 'bg-blue-500 hover:bg-blue-600',
    success: 'bg-green-500 hover:bg-green-600',
    warning: 'bg-amber-500 hover:bg-amber-600',
    error: 'bg-red-500 hover:bg-red-600',
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm" showCloseButton={false}>
      <div className="p-5">
        <div className="flex items-start gap-3">
          {icons[type]}
          <div className="flex-1">
            {title && (
              <h4 className={cn('font-semibold mb-1', theme === 'dark' ? 'text-slate-100' : 'text-slate-800')}>
                {title}
              </h4>
            )}
            <p className={cn('text-sm', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
              {message}
            </p>
          </div>
        </div>

        <div className="flex justify-end mt-4">
          <button
            onClick={onClose}
            className={cn('px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors', buttonColors[type])}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ==================== Confirm Dialog ====================

interface ConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title?: string
  message: string
  type?: 'warning' | 'danger'
  confirmText?: string
  cancelText?: string
  isLoading?: boolean
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  type = 'warning',
  confirmText = '确定',
  cancelText = '取消',
  isLoading = false,
}) => {
  const { theme } = useThemeStore()

  const handleConfirm = useCallback(() => {
    if (!isLoading) {
      onConfirm()
    }
  }, [isLoading, onConfirm])

  const icons = {
    warning: <AlertTriangle className="text-amber-500" size={24} />,
    danger: <AlertCircle className="text-red-500" size={24} />,
  }

  const buttonColors = {
    warning: 'bg-amber-500 hover:bg-amber-600',
    danger: 'bg-red-500 hover:bg-red-600',
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm" showCloseButton={false} closeOnOverlayClick={!isLoading}>
      <div className="p-5">
        <div className="flex items-start gap-3">
          {icons[type]}
          <div className="flex-1">
            {title && (
              <h4 className={cn('font-semibold mb-1', theme === 'dark' ? 'text-slate-100' : 'text-slate-800')}>
                {title}
              </h4>
            )}
            <p className={cn('text-sm', theme === 'dark' ? 'text-slate-300' : 'text-slate-600')}>
              {message}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            disabled={isLoading}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              theme === 'dark'
                ? 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700',
              isLoading && 'opacity-50 cursor-not-allowed'
            )}
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            disabled={isLoading}
            className={cn(
              'px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors',
              buttonColors[type],
              isLoading && 'opacity-50 cursor-not-allowed'
            )}
          >
            {isLoading ? '处理中...' : confirmText}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ==================== Toast 通知 ====================

interface ToastProps {
  message: string
  type?: AlertType
  isVisible: boolean
  onClose: () => void
  duration?: number
}

export const Toast: React.FC<ToastProps> = ({
  message,
  type = 'info',
  isVisible,
  onClose,
  duration = 3000,
}) => {
  const { theme } = useThemeStore()

  useEffect(() => {
    if (isVisible && duration > 0) {
      const timer = setTimeout(onClose, duration)
      return () => clearTimeout(timer)
    }
  }, [isVisible, duration, onClose])

  if (!isVisible) return null

  const icons = {
    info: <Info size={18} />,
    success: <CheckCircle size={18} />,
    warning: <AlertTriangle size={18} />,
    error: <AlertCircle size={18} />,
  }

  const colors = {
    info: theme === 'dark' ? 'bg-blue-900/90 text-blue-100 border-blue-700' : 'bg-blue-50 text-blue-800 border-blue-200',
    success: theme === 'dark' ? 'bg-green-900/90 text-green-100 border-green-700' : 'bg-green-50 text-green-800 border-green-200',
    warning: theme === 'dark' ? 'bg-amber-900/90 text-amber-100 border-amber-700' : 'bg-amber-50 text-amber-800 border-amber-200',
    error: theme === 'dark' ? 'bg-red-900/90 text-red-100 border-red-700' : 'bg-red-50 text-red-800 border-red-200',
  }

  return (
    <div className="fixed top-4 right-4 z-[100] animate-in slide-in-from-top-2 fade-in duration-200">
      <div
        className={cn(
          'flex items-center gap-2 px-4 py-3 rounded-lg border shadow-lg backdrop-blur-sm',
          colors[type]
        )}
      >
        {icons[type]}
        <span className="text-sm font-medium">{message}</span>
        <button onClick={onClose} className="ml-2 opacity-70 hover:opacity-100">
          <X size={16} />
        </button>
      </div>
    </div>
  )
}

// ==================== useModal Hook ====================

interface ModalState {
  alert: { isOpen: boolean; title?: string; message: string; type: AlertType }
  confirm: { isOpen: boolean; title?: string; message: string; type: 'warning' | 'danger'; onConfirm: () => void; isLoading: boolean }
  toast: { isVisible: boolean; message: string; type: AlertType }
}

const initialState: ModalState = {
  alert: { isOpen: false, message: '', type: 'info' },
  confirm: { isOpen: false, message: '', type: 'warning', onConfirm: () => {}, isLoading: false },
  toast: { isVisible: false, message: '', type: 'info' },
}

export const useModal = () => {
  const [state, setState] = React.useState<ModalState>(initialState)

  const showAlert = useCallback((message: string, options?: { title?: string; type?: AlertType }) => {
    setState((prev) => ({
      ...prev,
      alert: { isOpen: true, message, title: options?.title, type: options?.type || 'info' },
    }))
  }, [])

  const hideAlert = useCallback(() => {
    setState((prev) => ({
      ...prev,
      alert: { ...prev.alert, isOpen: false },
    }))
  }, [])

  const showConfirm = useCallback(
    (message: string, onConfirm: () => void | Promise<void>, options?: { title?: string; type?: 'warning' | 'danger' }) => {
      setState((prev) => ({
        ...prev,
        confirm: {
          isOpen: true,
          message,
          title: options?.title,
          type: options?.type || 'warning',
          onConfirm: async () => {
            setState((p) => ({ ...p, confirm: { ...p.confirm, isLoading: true } }))
            try {
              await onConfirm()
              setState((p) => ({ ...p, confirm: { ...p.confirm, isOpen: false, isLoading: false } }))
            } catch (e) {
              setState((p) => ({ ...p, confirm: { ...p.confirm, isLoading: false } }))
              throw e
            }
          },
          isLoading: false,
        },
      }))
    },
    []
  )

  const hideConfirm = useCallback(() => {
    setState((prev) => ({
      ...prev,
      confirm: { ...prev.confirm, isOpen: false },
    }))
  }, [])

  const showToast = useCallback((message: string, type: AlertType = 'info') => {
    setState((prev) => ({
      ...prev,
      toast: { isVisible: true, message, type },
    }))
  }, [])

  const hideToast = useCallback(() => {
    setState((prev) => ({
      ...prev,
      toast: { ...prev.toast, isVisible: false },
    }))
  }, [])

  const ModalRenderer = useCallback(
    () => (
      <>
        <AlertDialog
          isOpen={state.alert.isOpen}
          onClose={hideAlert}
          title={state.alert.title}
          message={state.alert.message}
          type={state.alert.type}
        />
        <ConfirmDialog
          isOpen={state.confirm.isOpen}
          onClose={hideConfirm}
          onConfirm={state.confirm.onConfirm}
          title={state.confirm.title}
          message={state.confirm.message}
          type={state.confirm.type}
          isLoading={state.confirm.isLoading}
        />
        <Toast
          isVisible={state.toast.isVisible}
          onClose={hideToast}
          message={state.toast.message}
          type={state.toast.type}
        />
      </>
    ),
    [state, hideAlert, hideConfirm, hideToast]
  )

  return {
    showAlert,
    showConfirm,
    showToast,
    ModalRenderer,
  }
}
