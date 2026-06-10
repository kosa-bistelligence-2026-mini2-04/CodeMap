import { memo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn, clampProgress, formatDurationMs } from '@/lib/utils';
import type { AgentName, AgentRuntimeStatus } from '@/types/contracts';

const AGENT_LABELS: Record<AgentName, string> = {
  static_analyzer: '静态分析',
  behavior_inferer: '行为推断',
  community_assessor: '社区评估',
  reporter: '报告生成',
};

const STATUS_COLORS = {
  pending: 'border-border bg-background',
  running: 'border-primary/40 bg-primary/5',
  completed: 'border-success/50 bg-success/5',
  failed: 'border-destructive/60 bg-destructive/5',
  degraded: 'border-warning/60 bg-warning/5',
} as const;

const STATUS_LABELS = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  degraded: '降级',
} as const;

export interface AgentStatusCardProps {
  agent: AgentRuntimeStatus;
  onRetry?: (name: AgentName) => void;
}

function AgentStatusCardImpl({ agent, onRetry }: AgentStatusCardProps) {
  const progress = clampProgress(agent.progress);
  const canRetry = agent.status === 'failed' && agent.name === 'behavior_inferer';

  return (
    <Card className={cn('transition-colors', STATUS_COLORS[agent.status])}>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">
            {AGENT_LABELS[agent.name]}
          </span>
          <span
            className="text-xs text-muted-foreground"
            aria-live="polite"
            data-status={agent.status}
          >
            {STATUS_LABELS[agent.status]}
          </span>
        </div>

        <div
          className="h-2 w-full overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${AGENT_LABELS[agent.name]}进度`}
        >
          <div
            className={cn(
              'h-full transition-all duration-300',
              agent.status === 'failed'
                ? 'bg-destructive'
                : agent.status === 'degraded'
                  ? 'bg-warning'
                  : 'bg-primary',
            )}
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{progress}%</span>
          <span>{formatDurationMs(agent.duration_ms)}</span>
        </div>

        {agent.stage_label && agent.status === 'running' && (
          <p className="animate-pulse text-[11px] italic text-muted-foreground/70">
            {agent.stage_label}
          </p>
        )}

        {agent.message && (
          <p className="line-clamp-2 text-xs text-muted-foreground">
            {agent.message}
          </p>
        )}

        {canRetry && onRetry && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onRetry(agent.name)}
          >
            重试
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export const AgentStatusCard = memo(AgentStatusCardImpl);
