import type { AIStreamCloseInfo } from '../../services/api/ai';
import { translate } from '../../i18n';

export interface AIStreamStatusInput {
  transportError: string | null;
  isConnected: boolean;
  lastCloseInfo: AIStreamCloseInfo | null;
  closeInterruptedRequest: boolean;
  roomVersion: number | null;
  snapshotRequired: boolean;
}

export interface AIStreamStatusView {
  tone: 'warning' | 'normal' | 'muted';
  headline: string;
  description: string;
  detail: string | null;
  badges: string[];
  showReplay: boolean;
}

export function getAIStreamStatusView({
  transportError,
  isConnected,
  lastCloseInfo,
  closeInterruptedRequest,
  roomVersion,
  snapshotRequired,
}: AIStreamStatusInput): AIStreamStatusView {
  const badges: string[] = [];

  if (roomVersion != null && roomVersion > 0) {
    badges.push(translate('streamStatus.roomVersion', { version: roomVersion }));
  }

  if (snapshotRequired) {
    badges.push(translate('streamStatus.baselineReplayRequired'));
    return {
      tone: 'warning',
      headline: translate('streamStatus.needsFreshBaseline'),
      description: translate('streamStatus.needsFreshBaselineDescription'),
      detail: transportError ?? null,
      badges,
      showReplay: true,
    };
  }

  if (isConnected) {
    badges.push(translate('streamStatus.liveStreamReady'));
    return {
      tone: 'normal',
      headline: translate('streamStatus.connected'),
      description: translate('streamStatus.connectedDescription'),
      detail: null,
      badges,
      showReplay: false,
    };
  }

  if (transportError && closeInterruptedRequest) {
    badges.push(translate('streamStatus.reconnectOnNextSend'));
    const detail =
      lastCloseInfo && lastCloseInfo.code !== 1000
        ? translate('streamStatus.closeCode', {
          code: lastCloseInfo.code,
          reason: lastCloseInfo.reason ?? '',
        })
        : null;
    return {
      tone: 'warning',
      headline: translate('streamStatus.disconnected'),
      description: transportError,
      detail,
      badges,
      showReplay: false,
    };
  }

  badges.push(
    transportError
      ? translate('streamStatus.reconnectOnNextSend')
      : translate('streamStatus.connectsOnDemand'),
  );
  return {
    tone: 'muted',
    headline: translate('streamStatus.standingBy'),
    description: translate('streamStatus.standingByDescription'),
    detail:
      transportError && lastCloseInfo && lastCloseInfo.code !== 1000
        ? translate('streamStatus.lastClose', {
          code: lastCloseInfo.code,
          reason: lastCloseInfo.reason ?? '',
        })
        : null,
    badges,
    showReplay: false,
  };
}
