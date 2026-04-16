import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { initializeTheme, teardownThemeListener, useThemeStore } from './useThemeStore';

const SYSTEM_THEME_QUERY = '(prefers-color-scheme: dark)';

type MockMediaQueryList = MediaQueryList & {
  dispatch: (matches: boolean) => void;
};

function installMatchMedia(initialMatches: boolean): MockMediaQueryList {
  let matches = initialMatches;
  const listeners = new Set<(event: MediaQueryListEvent) => void>();

  const mediaQuery = {
    get matches() {
      return matches;
    },
    media: SYSTEM_THEME_QUERY,
    onchange: null,
    addEventListener: vi.fn((_type: string, listener: EventListenerOrEventListenerObject) => {
      if (typeof listener === 'function') {
        listeners.add(listener as (event: MediaQueryListEvent) => void);
      }
    }),
    removeEventListener: vi.fn((_type: string, listener: EventListenerOrEventListenerObject) => {
      if (typeof listener === 'function') {
        listeners.delete(listener as (event: MediaQueryListEvent) => void);
      }
    }),
    addListener: vi.fn((listener: (event: MediaQueryListEvent) => void) => {
      listeners.add(listener);
    }),
    removeListener: vi.fn((listener: (event: MediaQueryListEvent) => void) => {
      listeners.delete(listener);
    }),
    dispatchEvent: vi.fn(() => true),
    dispatch(nextMatches: boolean) {
      matches = nextMatches;
      const event = { matches: nextMatches, media: SYSTEM_THEME_QUERY } as MediaQueryListEvent;
      listeners.forEach((listener) => listener(event));
    },
  } as unknown as MockMediaQueryList;

  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation(() => mediaQuery),
  });

  return mediaQuery;
}

function resetThemeStore() {
  teardownThemeListener();
  useThemeStore.setState({
    theme: 'light',
    preference: 'system',
  });
  document.documentElement.classList.remove('dark');
}

describe('useThemeStore', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    resetThemeStore();
  });

  afterEach(() => {
    resetThemeStore();
  });

  it('defaults to the current system theme on startup', () => {
    installMatchMedia(true);

    initializeTheme();

    expect(useThemeStore.getState().preference).toBe('system');
    expect(useThemeStore.getState().theme).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('migrates previously persisted explicit themes', () => {
    installMatchMedia(false);
    localStorage.setItem('theme-storage', JSON.stringify({
      state: {
        theme: 'dark',
      },
      version: 0,
    }));

    initializeTheme();

    expect(useThemeStore.getState().preference).toBe('dark');
    expect(useThemeStore.getState().theme).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('tracks system theme changes while following the system preference', () => {
    const mediaQuery = installMatchMedia(false);

    initializeTheme();
    mediaQuery.dispatch(true);

    expect(useThemeStore.getState().preference).toBe('system');
    expect(useThemeStore.getState().theme).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('persists an explicit override when the user toggles theme manually', () => {
    const mediaQuery = installMatchMedia(true);

    initializeTheme();
    useThemeStore.getState().toggleTheme();
    mediaQuery.dispatch(true);

    expect(useThemeStore.getState().preference).toBe('light');
    expect(useThemeStore.getState().theme).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);

    const persisted = JSON.parse(localStorage.getItem('theme-storage') ?? '{}') as {
      state?: { preference?: string };
    };
    expect(persisted.state?.preference).toBe('light');
  });
});
