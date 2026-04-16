import { useMemo, type CSSProperties, type ReactNode } from 'react';
import { Loader2, RefreshCw, Wifi, WifiOff } from 'lucide-react';

import { useI18n } from '../../i18n';
import { useConnectionStore, type ConnectionStatus as Status } from '../../stores/connection_store';
import './ConnectionStatus.css';

interface ConnectionStatusProps {
  mode?: 'icon' | 'badge' | 'full';
  className?: string;
  showOnlineCount?: boolean;
  showReconnectCount?: boolean;
}

interface StatusConfig {
  icon: ReactNode;
  label: string;
  color: string;
  animate?: boolean;
}

export function ConnectionStatus({
  mode = 'badge',
  className = '',
  showOnlineCount = false,
  showReconnectCount = false,
}: ConnectionStatusProps) {
  const { t } = useI18n();
  const { status, onlineUsers, reconnectCount } = useConnectionStore();

  const statusConfig = useMemo<Record<Status, StatusConfig>>(() => ({
    connected: {
      icon: <Wifi size={16} />,
      label: t('connectionStatus.connected'),
      color: 'var(--color-success, #22c55e)',
    },
    disconnected: {
      icon: <WifiOff size={16} />,
      label: t('connectionStatus.disconnected'),
      color: 'var(--color-error, #ef4444)',
    },
    connecting: {
      icon: <Loader2 size={16} />,
      label: t('connectionStatus.connecting'),
      color: 'var(--color-warning, #f59e0b)',
      animate: true,
    },
    reconnecting: {
      icon: <RefreshCw size={16} />,
      label: t('connectionStatus.reconnecting'),
      color: 'var(--color-warning, #f59e0b)',
      animate: true,
    },
  }), [t]);

  const config = statusConfig[status];

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

  if (mode === 'badge') {
    return (
      <span
        className={`connection-status-badge ${className} ${status}`}
        style={{ '--status-color': config.color } as CSSProperties}
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
            <span className="reconnect-info">
              {t('connectionStatus.reconnectAttempt', { count: reconnectCount })}
            </span>
          )}
        </span>
      </div>
      {showOnlineCount && status === 'connected' && (
        <div className="online-info">
          <span className="online-dot" />
          <span>{t('connectionStatus.onlineUsers', { count: onlineUsers })}</span>
        </div>
      )}
    </div>
  );
}

export default ConnectionStatus;
