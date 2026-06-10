import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RepoInput } from '../RepoInput';

const originalFetch = globalThis.fetch;

const FAKE_CATALOG = {
  provider: 'openai',
  base_url: 'https://api.openai.com/v1',
  default_model: 'gpt-5.4',
  models: [
    { id: 'gpt-5.4', label: 'GPT-5.4', hint: 'Flagship 1M context' },
    { id: 'gpt-5.4-mini', label: 'GPT-5.4 mini', hint: 'Cheaper mini tier' },
  ],
};

function mockModelsFetch(): void {
  globalThis.fetch = vi.fn(async (url: RequestInfo | URL) => {
    const href = typeof url === 'string' ? url : url.toString();
    if (href.includes('/api/models')) {
      return new Response(JSON.stringify(FAKE_CATALOG), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    return new Response('not found', { status: 404 });
  }) as unknown as typeof fetch;
}

describe('RepoInput', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockModelsFetch();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('switches between GitHub URL and local path modes', async () => {
    render(<RepoInput onSubmit={() => undefined} />);

    // Default mode is github
    expect(screen.getByPlaceholderText(/https:\/\/github\.com\/owner\/repo/)).toBeInTheDocument();

    // Switch to local
    fireEvent.click(screen.getByRole('tab', { name: '本地路径' }));
    expect(screen.getByPlaceholderText(/C:\\path\\to\\repo/)).toBeInTheDocument();
  });

  it('shows an error when submitting an invalid GitHub URL', async () => {
    render(<RepoInput onSubmit={() => undefined} />);

    const input = screen.getByLabelText('仓库 URL');
    fireEvent.change(input, { target: { value: 'not-a-url' } });
    fireEvent.blur(input);

    expect(
      await screen.findByText(/请输入有效的 GitHub 仓库 URL/),
    ).toBeInTheDocument();
  });

  it('calls onSubmit with source/path/model/force_refresh when valid', async () => {
    const onSubmit = vi.fn();
    render(<RepoInput onSubmit={onSubmit} />);

    // Wait for /api/models to resolve so selectedModel is populated
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());

    const input = screen.getByLabelText('仓库 URL');
    fireEvent.change(input, {
      target: { value: 'https://github.com/foo/bar' },
    });

    fireEvent.click(screen.getByRole('button', { name: /开始分析/ }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({
      source: 'github',
      path: 'https://github.com/foo/bar',
      force_refresh: false,
      model: 'gpt-5.4',
    });
  });
});
