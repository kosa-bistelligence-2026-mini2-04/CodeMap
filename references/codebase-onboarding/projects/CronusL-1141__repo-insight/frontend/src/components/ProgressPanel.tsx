import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AgentStatusCard } from './AgentStatusCard';
import { AGENT_NAMES } from '@/store/analysisStore';
import type { AgentName, AgentRuntimeStatus } from '@/types/contracts';

export interface ProgressPanelProps {
  jobId: string;
  agents: Record<AgentName, AgentRuntimeStatus>;
  wsConnected: boolean;
  wsRetries: number;
  onRetry?: (name: AgentName) => void;
}

export function ProgressPanel({
  jobId,
  agents,
  wsConnected,
  wsRetries,
  onRetry,
}: ProgressPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>分析进度</span>
          <span
            className="text-xs font-normal text-muted-foreground"
            aria-live="polite"
          >
            {wsConnected
              ? '实时'
              : wsRetries > 0
                ? `重连中 (${wsRetries}/5)`
                : '未连接'}
          </span>
        </CardTitle>
        <p className="truncate text-xs text-muted-foreground" title={jobId}>
          Job: {jobId}
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {AGENT_NAMES.map((name) => (
          <AgentStatusCard key={name} agent={agents[name]} onRetry={onRetry} />
        ))}
      </CardContent>
    </Card>
  );
}
