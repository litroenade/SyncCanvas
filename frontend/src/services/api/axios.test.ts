import { AxiosError } from 'axios';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { useLocaleStore } from '../../stores/useLocaleStore';
import { getRequestErrorMessage } from './axios';

function createAxiosError(status: number, data: unknown, message = 'Request failed') {
  return new AxiosError(
    message,
    'ERR_BAD_REQUEST',
    {} as never,
    undefined,
    {
      status,
      data,
      statusText: message,
      headers: {},
      config: {} as never,
    },
  );
}

describe('getRequestErrorMessage', () => {
  beforeEach(() => {
    useLocaleStore.setState({ locale: 'en-US' });
  });

  afterEach(() => {
    useLocaleStore.setState({ locale: 'en-US' });
  });

  it('prefers backend detail strings when they are present', () => {
    expect(
      getRequestErrorMessage(
        createAxiosError(400, { detail: 'Room password is incorrect.' }),
        'Fallback',
      ),
    ).toBe('Room password is incorrect.');
  });

  it('maps axios network failures to localized copy', () => {
    expect(
      getRequestErrorMessage(new AxiosError('Network Error', 'ERR_NETWORK'), 'Fallback'),
    ).toBe('Network connection failed. Please check the server and try again.');
  });

  it('maps fetch transport failures to the same localized network copy', () => {
    expect(getRequestErrorMessage(new TypeError('Failed to fetch'), 'Fallback')).toBe(
      'Network connection failed. Please check the server and try again.',
    );
  });

  it('maps status-based errors when the backend does not return detail', () => {
    expect(getRequestErrorMessage(createAxiosError(404, {}), 'Fallback')).toBe(
      'Requested resource was not found.',
    );
  });
});
