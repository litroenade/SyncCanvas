import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export type ThemeMode = 'light' | 'dark';
export type ThemePreference = ThemeMode | 'system';

interface ThemeState {
  theme: ThemeMode;
  preference: ThemePreference;
  toggleTheme: () => void;
  setTheme: (theme: ThemeMode) => void;
}

interface PersistedThemeSnapshot {
  preference?: unknown;
  theme?: unknown;
}

const STORAGE_KEY = 'theme-storage';
const SYSTEM_THEME_QUERY = '(prefers-color-scheme: dark)';

let systemThemeMediaQuery: MediaQueryList | null = null;
let systemThemeListener: ((event: MediaQueryListEvent) => void) | null = null;

const isThemeMode = (value: unknown): value is ThemeMode => value === 'light' || value === 'dark';

const isThemePreference = (value: unknown): value is ThemePreference =>
  value === 'system' || isThemeMode(value);

export const getSystemTheme = (): ThemeMode => {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return 'light';
  }
  return window.matchMedia(SYSTEM_THEME_QUERY).matches ? 'dark' : 'light';
};

export const resolveTheme = (preference: ThemePreference): ThemeMode =>
  preference === 'system' ? getSystemTheme() : preference;

const applyThemeClass = (theme: ThemeMode) => {
  if (typeof document === 'undefined') {
    return;
  }
  document.documentElement.classList.toggle('dark', theme === 'dark');
};

const resolveStoredPreference = (snapshot?: PersistedThemeSnapshot | null): ThemePreference => {
  if (!snapshot) {
    return 'system';
  }
  if (isThemePreference(snapshot.preference)) {
    return snapshot.preference;
  }
  if (isThemeMode(snapshot.theme)) {
    return snapshot.theme;
  }
  return 'system';
};

const readStoredPreference = (): ThemePreference => {
  if (typeof window === 'undefined') {
    return 'system';
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return 'system';
    }

    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === 'object' && 'state' in parsed) {
      return resolveStoredPreference(
        (parsed as { state?: PersistedThemeSnapshot | null }).state,
      );
    }
    return resolveStoredPreference(parsed as PersistedThemeSnapshot);
  } catch {
    return 'system';
  }
};

const getInitialThemeState = () => {
  const preference = readStoredPreference();
  return {
    preference,
    theme: resolveTheme(preference),
  };
};

const detachSystemThemeListener = () => {
  if (!systemThemeMediaQuery || !systemThemeListener) {
    return;
  }

  if (typeof systemThemeMediaQuery.removeEventListener === 'function') {
    systemThemeMediaQuery.removeEventListener('change', systemThemeListener);
  } else {
    systemThemeMediaQuery.removeListener(systemThemeListener);
  }

  systemThemeMediaQuery = null;
  systemThemeListener = null;
};

const attachSystemThemeListener = () => {
  if (
    typeof window === 'undefined'
    || typeof window.matchMedia !== 'function'
    || systemThemeListener
  ) {
    return;
  }

  const mediaQuery = window.matchMedia(SYSTEM_THEME_QUERY);
  const listener = (event: MediaQueryListEvent) => {
    if (useThemeStore.getState().preference !== 'system') {
      return;
    }

    const nextTheme: ThemeMode = event.matches ? 'dark' : 'light';
    applyThemeClass(nextTheme);
    useThemeStore.setState({ theme: nextTheme });
  };

  if (typeof mediaQuery.addEventListener === 'function') {
    mediaQuery.addEventListener('change', listener);
  } else {
    mediaQuery.addListener(listener);
  }

  systemThemeMediaQuery = mediaQuery;
  systemThemeListener = listener;
};

export const initializeTheme = () => {
  const preference = readStoredPreference();
  const theme = resolveTheme(preference);

  applyThemeClass(theme);
  useThemeStore.setState({ preference, theme });
  attachSystemThemeListener();
};

export const teardownThemeListener = () => {
  detachSystemThemeListener();
};

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      ...getInitialThemeState(),
      toggleTheme: () => {
        const nextTheme: ThemeMode = get().theme === 'dark' ? 'light' : 'dark';
        applyThemeClass(nextTheme);
        set({ theme: nextTheme, preference: nextTheme });
      },
      setTheme: (theme) => {
        applyThemeClass(theme);
        set({ theme, preference: theme });
      },
    }),
    {
      name: STORAGE_KEY,
      version: 1,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ preference: state.preference }),
      merge: (persistedState, currentState) => {
        const snapshot = persistedState as PersistedThemeSnapshot | undefined;
        const preference = resolveStoredPreference(snapshot);
        return {
          ...currentState,
          preference,
          theme: resolveTheme(preference),
        };
      },
    },
  ),
);
