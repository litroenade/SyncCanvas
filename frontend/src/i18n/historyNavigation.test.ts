import { describe, expect, it } from 'vitest';

import { translateWithLocale } from './core';

describe('merged history navigation copy', () => {
  it('returns the shared history entry labels', () => {
    expect(translateWithLocale('en-US', 'canvas.menu.history')).toBe('History');
    expect(translateWithLocale('en-US', 'canvas.sidebar.history')).toBe('History');
    expect(translateWithLocale('en-US', 'history.view.versions')).toBe('Versions');
    expect(translateWithLocale('en-US', 'history.view.activity')).toBe('Activity');
  });
});
