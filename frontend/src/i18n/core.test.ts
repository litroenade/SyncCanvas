import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  formatRelativeTimeLabel,
  normalizeLocale,
  translateWithLocale,
} from './core';

describe('i18n core', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('normalizes browser locales to supported app locales', () => {
    expect(normalizeLocale('zh-CN')).toBe('zh-CN');
    expect(normalizeLocale('zh-TW')).toBe('zh-CN');
    expect(normalizeLocale('en')).toBe('en-US');
    expect(normalizeLocale(undefined)).toBe('en-US');
  });

  it('returns localized copy for both locales', () => {
    expect(translateWithLocale('en-US', 'canvas.roomBadge', { id: 'abcd1234' })).toBe('Room abcd1234');
    expect(translateWithLocale('zh-CN', 'canvas.roomBadge', { id: 'abcd1234' })).toBe('房间 abcd1234');
    expect(translateWithLocale('zh-CN', 'diagramAgent.toolCalls', { count: 2 })).toBe('2 个工具调用');
    expect(translateWithLocale('en-US', 'toolProgress.running', { done: 1, total: 3 })).toBe('Running... (1/3)');
    expect(translateWithLocale('zh-CN', 'collabEvents.memberFilter.all')).toBe('所有成员');
    expect(translateWithLocale('en-US', 'modelSettings.title')).toBe('Model settings');
    expect(translateWithLocale('zh-CN', 'modal.confirm')).toBe('确定');
    expect(translateWithLocale('en-US', 'settings.modelPlaceholder')).toBe(
      'For example: Qwen/Qwen2.5-14B-Instruct',
    );
    expect(translateWithLocale('zh-CN', 'virtualCanvas.dragPreviewTitle')).toBe('将预览拖到画布');
    expect(translateWithLocale('en-US', 'aiStream.connectionError')).toBe(
      'AI connection error, please retry.',
    );
    expect(translateWithLocale('en-US', 'locale.switchToChinese')).toBe('Switch to Chinese');
    expect(translateWithLocale('en-US', 'diagramAgent.diffExplanation.summary')).toBe('Summary');
    expect(translateWithLocale('en-US', 'diagramAgent.diffExplanation.note.deterministicSeed')).toBe(
      'This is a fallback preview. You can continue refining it with another prompt.',
    );
    expect(translateWithLocale('zh-CN', 'connectionStatus.reconnectAttempt', { count: 3 })).toBe(
      '第 3 次重连尝试',
    );
  });

  it('formats relative timestamps with locale-aware labels', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-15T10:00:00.000Z'));

    const threeMinutesAgo = Date.now() - 3 * 60 * 1000;
    const justNow = Date.now() - 10 * 1000;

    expect(formatRelativeTimeLabel('en-US', justNow)).toBe('Just now');
    expect(formatRelativeTimeLabel('en-US', threeMinutesAgo)).toBe('3m ago');
    expect(formatRelativeTimeLabel('zh-CN', justNow)).toBe('刚刚');
    expect(formatRelativeTimeLabel('zh-CN', threeMinutesAgo)).toBe('3 分钟前');
  });
});
