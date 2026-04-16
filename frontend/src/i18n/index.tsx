import {
  createContext,
  useContext,
  useMemo,
  type ReactNode,
} from 'react';

import {
  formatDateTimeLabel,
  formatRelativeTimeLabel,
  getExcalidrawLanguage,
  translateWithLocale,
  type AppLocale,
  type TranslationParams,
} from './core';
import { useLocaleStore } from '../stores/useLocaleStore';

interface I18nContextValue {
  locale: AppLocale;
  setLocale: (locale: AppLocale) => void;
  t: (key: string, params?: TranslationParams) => string;
  excalidrawLanguage: 'zh-CN' | 'en-US';
  formatRelativeTime: (timestamp: number) => string;
  formatDateTime: (timestamp: number) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const locale = useLocaleStore((state) => state.locale);
  const setLocale = useLocaleStore((state) => state.setLocale);

  const value = useMemo<I18nContextValue>(() => ({
    locale,
    setLocale,
    t: (key, params = {}) => translateWithLocale(locale, key, params),
    excalidrawLanguage: getExcalidrawLanguage(locale),
    formatRelativeTime: (timestamp) => formatRelativeTimeLabel(locale, timestamp),
    formatDateTime: (timestamp) => formatDateTimeLabel(locale, timestamp),
  }), [locale, setLocale]);

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return context;
}

export function translate(key: string, params: TranslationParams = {}): string {
  const locale = useLocaleStore.getState().locale;
  return translateWithLocale(locale, key, params);
}

export type { AppLocale } from './core';
