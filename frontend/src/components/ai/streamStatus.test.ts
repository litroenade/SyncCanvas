import { beforeEach, describe, expect, it } from 'vitest';

import { getAIStreamStatusView } from './streamStatus';
import { useLocaleStore } from '../../stores/useLocaleStore';

describe('getAIStreamStatusView', () => {
  beforeEach(() => {
    useLocaleStore.getState().setLocale('en-US');
  });

  it('marks snapshot-required sessions as replay-blocked', () => {
    const status = getAIStreamStatusView({
      transportError: 'Room snapshot is stale.',
      isConnected: false,
      lastCloseInfo: {
        code: 1008,
        reason: 'RECONNECT_REQUIRES_SNAPSHOT',
        wasClean: true,
        room_version: 42,
        snapshot_required: true,
      },
      closeInterruptedRequest: true,
      roomVersion: 42,
      snapshotRequired: true,
    });

    expect(status.tone).toBe('warning');
    expect(status.showReplay).toBe(true);
    expect(status.badges).toEqual(['Room v42', 'Baseline replay required']);
    expect(status.description).toContain('Replay HEAD');
  });

  it('returns a ready status for active connections', () => {
    const status = getAIStreamStatusView({
      transportError: null,
      isConnected: true,
      lastCloseInfo: null,
      closeInterruptedRequest: false,
      roomVersion: 7,
      snapshotRequired: false,
    });

    expect(status.tone).toBe('normal');
    expect(status.badges).toEqual(['Room v7', 'Live stream ready']);
    expect(status.showReplay).toBe(false);
    expect(status.detail).toBeNull();
  });

  it('shows a warning when a disconnect interrupts an in-flight request', () => {
    const status = getAIStreamStatusView({
      transportError: '你没有该房间访问权限。',
      isConnected: false,
      lastCloseInfo: {
        code: 1008,
        reason: 'room_membership_required',
        wasClean: true,
      },
      closeInterruptedRequest: true,
      roomVersion: null,
      snapshotRequired: false,
    });

    expect(status.tone).toBe('warning');
    expect(status.headline).toBe('AI stream disconnected');
    expect(status.detail).toBe('Close code 1008 (room_membership_required)');
    expect(status.badges).toContain('Reconnect on next send');
  });

  it('keeps post-request transport closes in muted standby state', () => {
    const status = getAIStreamStatusView({
      transportError: 'AI connection error, please retry.',
      isConnected: false,
      lastCloseInfo: {
        code: 1012,
        reason: '',
        wasClean: false,
      },
      closeInterruptedRequest: false,
      roomVersion: 0,
      snapshotRequired: false,
    });

    expect(status.tone).toBe('muted');
    expect(status.headline).toBe('AI stream standing by');
    expect(status.badges).toEqual(['Reconnect on next send']);
    expect(status.detail).toBe('Last close 1012');
  });

  it('falls back to a muted on-demand state before the first connection', () => {
    const status = getAIStreamStatusView({
      transportError: null,
      isConnected: false,
      lastCloseInfo: null,
      closeInterruptedRequest: false,
      roomVersion: null,
      snapshotRequired: false,
    });

    expect(status.tone).toBe('muted');
    expect(status.badges).toEqual(['Connects on demand']);
    expect(status.showReplay).toBe(false);
  });
});
