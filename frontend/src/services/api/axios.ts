import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from 'axios';

import { config } from '../../config/env';
import { translate } from '../../i18n';

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (requestConfig: InternalAxiosRequestConfig) => requestConfig,
  (error: AxiosError) => {
    console.error('[API] request configuration error:', error);
    return Promise.reject(error);
  },
);

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ApiError>) => {
    const status = error.response?.status;
    const message = error.response?.data?.message || error.message;

    if (status === 403) {
      console.error('[API] forbidden:', message);
    }

    if (status && status >= 500) {
      console.error('[API] server error:', message);
    }

    return Promise.reject(error);
  },
);

export const getAuthHeaders = (): Record<string, string> => ({});

function getStringFromUnknown(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (Array.isArray(value)) {
    const parts = value
      .map((item) => getStringFromUnknown(item))
      .filter((item): item is string => Boolean(item));
    return parts.length > 0 ? parts.join(', ') : null;
  }

  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return (
      getStringFromUnknown(record.detail)
      ?? getStringFromUnknown(record.message)
      ?? getStringFromUnknown(record.error)
      ?? getStringFromUnknown(record.msg)
    );
  }

  return null;
}

function isNetworkFailureMessage(message: string): boolean {
  const normalized = message.trim().toLowerCase();
  return (
    normalized === 'failed to fetch'
    || normalized === 'network error'
    || normalized === 'load failed'
    || normalized.includes('networkerror')
  );
}

export function getRequestErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = getStringFromUnknown(error.response?.data);
    if (detail) {
      return detail;
    }

    if (error.code === 'ECONNABORTED') {
      return translate('api.timeoutError');
    }

    if (!error.response || error.code === AxiosError.ERR_NETWORK) {
      return translate('api.networkError');
    }

    switch (error.response.status) {
      case 401:
        return translate('api.unauthorized');
      case 403:
        return translate('api.forbidden');
      case 404:
        return translate('api.notFound');
      default:
        if (error.response.status >= 500) {
          return translate('api.serverError');
        }
    }

    return getStringFromUnknown(error.message) ?? fallback;
  }

  if (error instanceof Error) {
    if (isNetworkFailureMessage(error.message)) {
      return translate('api.networkError');
    }
    return getStringFromUnknown(error.message) ?? fallback;
  }

  return fallback;
}
