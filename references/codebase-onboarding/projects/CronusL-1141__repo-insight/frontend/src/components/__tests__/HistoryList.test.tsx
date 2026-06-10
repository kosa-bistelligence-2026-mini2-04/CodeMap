import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { HistoryList } from '../HistoryList';

const originalFetch = globalThis.fetch;

function mockFetchJson(payload: unknown): void {
  globalThis.fetch = vi.fn(async () =>
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  ) as unknown as typeof fetch;
}

describe('HistoryList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('shows empty-state copy when API returns no items', async () => {
    mockFetchJson({ items: [] });
    render(<HistoryList onSelect={() => undefined} />);

    await waitFor(() =>
      expect(screen.getByText('暂无历史记录')).toBeInTheDocument(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/analyses?limit=30');
  });

  it('invokes onSelect with the clicked analysis job_id', async () => {
    mockFetchJson({
      items: [
        {
          job_id: 'job-abc-123',
          source: 'github',
          path: 'https://github.com/foo/bar',
          status: 'completed',
          created_at: Math.floor(Date.now() / 1000) - 120,
          completed_at: Math.floor(Date.now() / 1000) - 60,
          total_pipeline_ms: 83_400,
          error_message: null,
          model_used: 'gpt-5.4',
          force_refresh: false,
        },
      ],
    });

    const onSelect = vi.fn();
    render(<HistoryList onSelect={onSelect} />);

    // Wait for the row to render
    const row = await screen.findByRole('button', { name: /foo\/bar/ });
    fireEvent.click(row);
    expect(onSelect).toHaveBeenCalledWith('job-abc-123');
  });
});
