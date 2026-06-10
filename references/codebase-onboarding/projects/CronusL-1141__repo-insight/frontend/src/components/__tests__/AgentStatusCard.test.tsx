import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentStatusCard } from '../AgentStatusCard';
import type { AgentRuntimeStatus } from '@/types/contracts';

function makeAgent(overrides: Partial<AgentRuntimeStatus> = {}): AgentRuntimeStatus {
  return {
    name: 'static_analyzer',
    status: 'running',
    progress: 42,
    stage_label: '扫描 utils 模块中…',
    duration_ms: 1234,
    ...overrides,
  };
}

describe('AgentStatusCard', () => {
  it('renders the Chinese agent label and progress percentage', () => {
    render(<AgentStatusCard agent={makeAgent()} />);
    expect(screen.getByText('静态分析')).toBeInTheDocument();
    expect(screen.getByText('42%')).toBeInTheDocument();
  });

  it('shows stage_label while status is running', () => {
    render(<AgentStatusCard agent={makeAgent({ status: 'running' })} />);
    expect(screen.getByText('扫描 utils 模块中…')).toBeInTheDocument();
  });

  it('hides stage_label when status is completed', () => {
    render(
      <AgentStatusCard
        agent={makeAgent({ status: 'completed', progress: 100 })}
      />,
    );
    expect(screen.queryByText('扫描 utils 模块中…')).not.toBeInTheDocument();
    expect(screen.getByText('已完成')).toBeInTheDocument();
  });

  it('exposes aria-valuenow equal to clamped progress on the progressbar', () => {
    render(<AgentStatusCard agent={makeAgent({ progress: 73 })} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '73');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
  });

  it('clamps out-of-range progress values', () => {
    render(<AgentStatusCard agent={makeAgent({ progress: 250 })} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '100');
  });
});
