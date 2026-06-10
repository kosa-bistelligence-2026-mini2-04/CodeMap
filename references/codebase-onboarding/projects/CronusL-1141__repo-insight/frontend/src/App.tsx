import { useCallback, useState } from 'react';
import { useAnalysisJob } from '@/hooks/useAnalysisJob';
import { useAnalysisStore } from '@/store/analysisStore';
import { RepoInput } from '@/components/RepoInput';
import { ProgressPanel } from '@/components/ProgressPanel';
import { ReportViewer } from '@/components/ReportViewer';
import { HistoryList } from '@/components/HistoryList';
import { Card, CardContent } from '@/components/ui/card';
import type { ReportJsonResponse } from '@/types/contracts';

function EmptyState() {
  return (
    <Card className="h-full">
      <CardContent className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-2 text-center">
        <h2 className="text-lg font-semibold">尚未生成报告</h2>
        <p className="max-w-md text-sm text-muted-foreground">
          在左侧输入本地 Git 路径或 GitHub 仓库 URL，点击「开始分析」。
          四个 Agent 将并发执行静态扫描、行为推断、社区评估与报告生成，
          总预算 120 秒。
        </p>
        <p className="mt-4 max-w-md text-xs text-muted-foreground">
          或者从下方"历史记录"中选择一条已完成的分析查看。
        </p>
      </CardContent>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <Card className="h-full">
      <CardContent className="flex h-full min-h-[60vh] flex-col gap-4 p-6">
        <div className="h-6 w-48 animate-pulse rounded bg-muted" />
        <div className="h-4 w-72 animate-pulse rounded bg-muted" />
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="h-24 animate-pulse rounded bg-muted" />
          <div className="h-24 animate-pulse rounded bg-muted" />
        </div>
        <div className="mt-2 h-64 animate-pulse rounded bg-muted" />
        <p className="text-center text-xs text-muted-foreground">
          Agents 正在分析，请稍候…
        </p>
      </CardContent>
    </Card>
  );
}

export default function App() {
  const { submit, wsConnected, wsRetries } = useAnalysisJob();

  const jobId = useAnalysisStore((s) => s.jobId);
  const status = useAnalysisStore((s) => s.status);
  const agents = useAnalysisStore((s) => s.agents);
  const report = useAnalysisStore((s) => s.report);
  const htmlReport = useAnalysisStore((s) => s.htmlReport);
  const error = useAnalysisStore((s) => s.error);
  const setReport = useAnalysisStore((s) => s.setReport);

  const running = status === 'queued' || status === 'running';

  // Bump this when a new analysis completes to refresh the history list
  const [refreshToken, setRefreshToken] = useState(0);
  const [historicalJobId, setHistoricalJobId] = useState<string | null>(null);

  // Refresh history when a new report lands
  if (report && refreshToken === 0) {
    setTimeout(() => setRefreshToken((r) => r + 1), 0);
  }

  // Load a historical analysis from the persistent store
  const loadHistorical = useCallback(
    async (clickedJobId: string) => {
      try {
        const resp = await fetch(`/api/report/${clickedJobId}?format=json`);
        if (!resp.ok) {
          alert(`加载失败: ${resp.status}`);
          return;
        }
        const data = (await resp.json()) as ReportJsonResponse;
        setReport(data);
        setHistoricalJobId(clickedJobId);
      } catch (e) {
        alert(`加载失败: ${e instanceof Error ? e.message : String(e)}`);
      }
    },
    [setReport],
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between px-4 py-3 lg:px-8">
          <h1 className="text-lg font-semibold">RepoInsight</h1>
          <span className="text-xs text-muted-foreground">
            Python 仓库智能分析
          </span>
        </div>
      </header>

      <main className="mx-auto grid max-w-screen-2xl gap-6 p-4 lg:grid-cols-[384px_1fr] lg:p-8">
        <aside className="space-y-4">
          <RepoInput onSubmit={submit} disabled={running} />
          {jobId && (
            <ProgressPanel
              jobId={jobId}
              agents={agents}
              wsConnected={wsConnected}
              wsRetries={wsRetries}
            />
          )}
          {error && (
            <div className="rounded-md border border-destructive/60 bg-destructive/5 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          <HistoryList
            onSelect={loadHistorical}
            activeJobId={historicalJobId ?? jobId}
            refreshToken={refreshToken}
          />
        </aside>

        <section className="min-h-[60vh]">
          {report ? (
            <ReportViewer report={report} htmlReport={htmlReport} />
          ) : running ? (
            <LoadingSkeleton />
          ) : (
            <EmptyState />
          )}
        </section>
      </main>
    </div>
  );
}
