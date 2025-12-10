/**
 * ConnectionStatus - 连接状态指示器组件
 * 
 * 显示 WebSocket 连接状态，支持多种显示模式。
 */

import { useMemo } from 'react';
import { Wifi, WifiOff, Loader2, RefreshCw } from 'lucide-react';
import { useConnectionStore, type ConnectionStatus as Status } from '../../stores/connection_store';
import './ConnectionStatus.css';

// ==================== 类型定义 ====================

interface ConnectionStatusProps {
    /** 显示模式 */
    mode?: 'icon' | 'badge' | 'full';
    /** 自定义样式 */
    className?: string;
    /** 是否显示在线人数 */
    showOnlineCount?: boolean;
    /** 是否显示重连次数 */
    showReconnectCount?: boolean;
}

interface StatusConfig {
    icon: React.ReactNode;
    label: string;
    color: string;
    animate?: boolean;
}

// ==================== 状态配置 ====================

const STATUS_CONFIG: Record<Status, StatusConfig> = {
    connected: {
        icon: <Wifi size={16} />,
        label: '已连接',
        color: 'var(--color-success, #22c55e)',
    },
    disconnected: {
        icon: <WifiOff size={16} />,
        label: '未连接',
        color: 'var(--color-error, #ef4444)',
    },
    connecting: {
        icon: <Loader2 size={16} />,
        label: '连接中',
        color: 'var(--color-warning, #f59e0b)',
        animate: true,
    },
    reconnecting: {
        icon: <RefreshCw size={16} />,
        label: '重连中',
        color: 'var(--color-warning, #f59e0b)',
        animate: true,
    },
};

// ==================== 主组件 ====================

export function ConnectionStatus({
    mode = 'badge',
    className = '',
    showOnlineCount = false,
    showReconnectCount = false,
}: ConnectionStatusProps) {
    const { status, onlineUsers, reconnectCount } = useConnectionStore();

    const config = useMemo(() => STATUS_CONFIG[status], [status]);

    // 仅图标模式
    if (mode === 'icon') {
        return (
            <span
                className={`connection-status-icon ${className} ${config.animate ? 'animate' : ''}`}
                style={{ color: config.color }}
                title={config.label}
            >
                {config.icon}
            </span>
        );
    }

    // 徽章模式
    if (mode === 'badge') {
        return (
            <span
                className={`connection-status-badge ${className} ${status}`}
                style={{ '--status-color': config.color } as React.CSSProperties}
            >
                <span className={`status-icon ${config.animate ? 'animate' : ''}`}>
                    {config.icon}
                </span>
                <span className="status-label">{config.label}</span>
                {showOnlineCount && status === 'connected' && onlineUsers > 0 && (
                    <span className="online-count">{onlineUsers}</span>
                )}
                {showReconnectCount && reconnectCount > 0 && (
                    <span className="reconnect-count">#{reconnectCount}</span>
                )}
            </span>
        );
    }

    // 完整模式
    return (
        <div className={`connection-status-full ${className} ${status}`}>
            <div className="status-main">
                <span
                    className={`status-icon ${config.animate ? 'animate' : ''}`}
                    style={{ color: config.color }}
                >
                    {config.icon}
                </span>
                <span className="status-text">
                    <span className="status-label">{config.label}</span>
                    {status === 'reconnecting' && reconnectCount > 0 && (
                        <span className="reconnect-info">第 {reconnectCount} 次尝试</span>
                    )}
                </span>
            </div>
            {showOnlineCount && status === 'connected' && (
                <div className="online-info">
                    <span className="online-dot"></span>
                    <span>{onlineUsers} 人在线</span>
                </div>
            )}
        </div>
    );
}

export default ConnectionStatus;
