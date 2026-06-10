import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface AnalysisRow {
  job_id: string;
  source: 'local' | 'github';
  path: string;
  status: 'running' | 'completed' | 'failed';
  created_at: number;
  completed_at: number | null;
  total_pipeline_ms: number | null;
  error_message: string | null;
  model_used: string | null;
  force_refresh: boolean;
}

export interface HistoryListProps {
  /** Callback when a user clicks a past analysis to load. Parent fetches the full report. */
  onSelect: (jobId: string) => void;
  /** Currently selected job_id (for active highlight) */
  activeJobId?: string | null;
  /** Reload trigger — bump this number when a new analysis completes */
  refreshToken?: number;
}

function shortenPath(p: string, maxLen = 36): string {
  const normalized = p.replace(/\\/g, '/');
  if (normalized.length <= maxLen) return normalized;
  return '…' + normalized.slice(-(maxLen - 1));
}

function formatRelativeTime(unixSeconds: number): string {
  const delta = Date.now() / 1000 - unixSeconds;
  if (delta < 60) return '刚刚';
  if (delta < 3600) return `${Math.floor(delta / 60)} 分钟前`;
  if (delta < 86400) return `${Math.floor(delta / 3600)} 小时前`;
  if (delta < 604800) return `${Math.floor(delta / 86400)} 天前`;
  return new Date(unixSeconds * 1000).toLocaleDateString();
}

const STATUS_COLORS: Record<AnalysisRow['status'], string> = {
  running: 'text-blue-600 bg-blue-50 dark:bg-blue-950/20',
  completed: 'text-green-600 bg-green-50 dark:bg-green-950/20',
  failed: 'text-red-600 bg-red-50 dark:bg-red-950/20',
};

const STATUS_LABELS: Record<AnalysisRow['status'], string> = {
  running: '运行中',
  completed: '已完成',
  failed: '失败',
};

export function HistoryList({ onSelect, activeJobId, refreshToken = 0 }: HistoryListProps) {
  const [items, setItems] = useState<AnalysisRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch('/api/analyses?limit=30');
      if (!resp.ok) throw new Error(`${resp.status}`);
      const data = await resp.json();
      setItems(data.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshToken]);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm">历史记录</CardTitle>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={load}
          disabled={loading}
          className="h-7 text-xs"
        >
          {loading ? '加载中' : '刷新'}
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        {error && (
          <p className="px-3 pb-2 text-xs text-destructive">加载失败：{error}</p>
        )}
        {items.length === 0 && !loading && !error && (
          <p className="px-3 pb-3 text-xs text-muted-foreground">暂无历史记录</p>
        )}
        <ul className="max-h-[380px] overflow-y-auto">
          {items.map((it) => (
            <li key={it.job_id}>
              <button
                type="button"
                onClick={() => onSelect(it.job_id)}
                className={cn(
                  'block w-full border-t border-border px-3 py-2 text-left transition-colors hover:bg-secondary',
                  activeJobId === it.job_id && 'bg-secondary',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs font-medium" title={it.path}>
                    {shortenPath(it.path)}
                  </span>
                  <span
                    className={cn(
                      'rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase',
                      STATUS_COLORS[it.status],
                    )}
                  >
                    {STATUS_LABELS[it.status]}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
                  <span>{formatRelativeTime(it.created_at)}</span>
                  {it.total_pipeline_ms != null && (
                    <span>{(it.total_pipeline_ms / 1000).toFixed(1)} s</span>
                  )}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
