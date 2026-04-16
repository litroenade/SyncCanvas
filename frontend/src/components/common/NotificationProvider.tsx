/* eslint-disable react-refresh/only-export-components */
/**
 * 模块名称: NotificationProvider
 * 主要功能: 全局通知系统提供者
 * 
 * 提供统一的 toast 通知，使用 React Context 和自定义 Hook 实现。
 */

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';

// ==================== 类型定义 ====================

/** 通知类型 */
type NotificationType = 'success' | 'error' | 'warning' | 'info';

/** 通知项 */
interface NotificationItem {
    id: string;
    type: NotificationType;
    message: string;
    duration: number;
}

/** 通知上下文 */
interface NotificationContextType {
    notify: (type: NotificationType, message: string, duration?: number) => void;
    success: (message: string, duration?: number) => void;
    error: (message: string, duration?: number) => void;
    warning: (message: string, duration?: number) => void;
    info: (message: string, duration?: number) => void;
}

// ==================== 配置 ====================

const notificationConfig = {
    maxNotifications: 5,
    defaultDuration: 3000,
    position: 'top-right' as const,
};

// ==================== Context ====================

const NotificationContext = createContext<NotificationContextType | null>(null);

// ==================== Hook ====================

/**
 * 使用通知系统的 Hook
 * 
 * @example
 * ```tsx
 * const { success, error } = useNotification();
 * success("操作成功");
 * error("操作失败");
 * ```
 */
export function useNotification(): NotificationContextType {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error('useNotification 必须在 NotificationProvider 内使用');
    }
    return context;
}

// ==================== 组件 ====================

interface NotificationProviderProps {
    children: ReactNode;
}

/**
 * 通知系统提供者组件
 */
export function NotificationProvider({ children }: NotificationProviderProps) {
    const [notifications, setNotifications] = useState<NotificationItem[]>([]);

    const removeNotification = useCallback((id: string) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    }, []);

    const notify = useCallback((
        type: NotificationType,
        message: string,
        duration: number = notificationConfig.defaultDuration
    ) => {
        const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const notification: NotificationItem = { id, type, message, duration };

        setNotifications(prev => {
            const newList = [...prev, notification];
            // 限制最大数量
            return newList.slice(-notificationConfig.maxNotifications);
        });

        // 自动移除
        if (duration > 0) {
            setTimeout(() => removeNotification(id), duration);
        }
    }, [removeNotification]);

    const success = useCallback((message: string, duration?: number) => {
        notify('success', message, duration);
    }, [notify]);

    const error = useCallback((message: string, duration?: number) => {
        notify('error', message, duration);
    }, [notify]);

    const warning = useCallback((message: string, duration?: number) => {
        notify('warning', message, duration);
    }, [notify]);

    const info = useCallback((message: string, duration?: number) => {
        notify('info', message, duration);
    }, [notify]);

    const contextValue: NotificationContextType = {
        notify,
        success,
        error,
        warning,
        info,
    };

    return (
        <NotificationContext.Provider value={contextValue}>
            {children}
            <NotificationContainer
                notifications={notifications}
                onRemove={removeNotification}
            />
        </NotificationContext.Provider>
    );
}

// ==================== 通知容器 ====================

interface NotificationContainerProps {
    notifications: NotificationItem[];
    onRemove: (id: string) => void;
}

function NotificationContainer({ notifications, onRemove }: NotificationContainerProps) {
    if (notifications.length === 0) return null;

    return (
        <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
            {notifications.map(notification => (
                <NotificationToast
                    key={notification.id}
                    notification={notification}
                    onRemove={onRemove}
                />
            ))}
        </div>
    );
}

// ==================== 单个通知 ====================

interface NotificationToastProps {
    notification: NotificationItem;
    onRemove: (id: string) => void;
}

function NotificationToast({ notification, onRemove }: NotificationToastProps) {
    const { id, type, message } = notification;

    const iconMap = {
        success: <CheckCircle className="w-5 h-5 text-green-500" />,
        error: <AlertCircle className="w-5 h-5 text-red-500" />,
        warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
        info: <Info className="w-5 h-5 text-blue-500" />,
    };

    const bgMap = {
        success: 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800',
        error: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
        warning: 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800',
        info: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
    };

    return (
        <div className={`
            flex items-start gap-3 p-4 rounded-lg border shadow-lg
            animate-in slide-in-from-right-5 fade-in duration-200
            ${bgMap[type]}
        `}>
            {iconMap[type]}
            <p className="flex-1 text-sm text-gray-800 dark:text-gray-200">{message}</p>
            <button
                onClick={() => onRemove(id)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    );
}

export default NotificationProvider;
