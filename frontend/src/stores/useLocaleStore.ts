import { create } from 'zustand';

import {
  type AppLocale,
  resolveInitialLocale,
} from '../i18n/core';

const STORAGE_KEY = 'sync-canvas-locale';

interface LocaleState {
  locale: AppLocale;
  initializeLocale: () => void;
  setLocale: (locale: AppLocale) => void;
}

function persistLocale(locale: AppLocale): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, locale);
  } catch {
    // Ignore localStorage access failures.
  }
  document.documentElement.lang = locale;
}

export const useLocaleStore = create<LocaleState>((set) => ({
  locale: 'en-US',
  initializeLocale: () => {
    const locale = resolveInitialLocale();
    persistLocale(locale);
    set({ locale });
  },
  setLocale: (locale) => {
    persistLocale(locale);
    set({ locale });
  },
}));

export function initializeLocale(): void {
  useLocaleStore.getState().initializeLocale();
}
