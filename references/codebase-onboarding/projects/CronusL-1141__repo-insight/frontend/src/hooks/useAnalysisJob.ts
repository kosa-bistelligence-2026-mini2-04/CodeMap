import { useCallback } from 'react';
import { startAnalysis, fetchReportJson, buildWsUrl } from '@/lib/api';
import { useAnalysisStore } from '@/store/analysisStore';
import type {
  AnalyzeRequest,
  ReportJsonResponse,
  WsEvent,
} from '@/types/contracts';
import { useWebSocket } from './useWebSocket';

interface UseAnalysisJobReturn {
  submit: (input: AnalyzeRequest) => Promise<void>;
  reset: () => void;
  wsConnected: boolean;
  wsRetries: number;
}

export function useAnalysisJob(): UseAnalysisJobReturn {
  const jobId = useAnalysisStore((s) => s.jobId);
  const status = useAnalysisStore((s) => s.status);
  const startJob = useAnalysisStore((s) => s.startJob);
  const upsertAgent = useAnalysisStore((s) => s.upsertAgent);
  const recordConflict = useAnalysisStore((s) => s.recordConflict);
  const recordDegraded = useAnalysisStore((s) => s.recordDegraded);
  const markCompleted = useAnalysisStore((s) => s.markCompleted);
  const markFailed = useAnalysisStore((s) => s.markFailed);
  const setReport = useAnalysisStore((s) => s.setReport);
  const reset = useAnalysisStore((s) => s.reset);

  const handleEvent = useCallback(
    (evt: WsEvent) => {
      switch (evt.type) {
        case 'agent_status':
          upsertAgent({
            name: evt.agent,
            status: evt.status,
            progress: evt.progress,
            stage_label: evt.stage_label,
          });
          break;
        case 'agent_completed':
          upsertAgent({
            name: evt.agent,
            status: 'completed',
            progress: 100,
            duration_ms: evt.duration_ms,
            message: evt.summary,
          });
          break;
        case 'conflict_detected':
          recordConflict(evt);
          break;
        case 'degraded':
          recordDegraded(evt);
          break;
        case 'completed': {
          markCompleted();
          fetchReportJson(evt.job_id)
            .then((data) => {
              if ('recommendations' in data) {
                setReport(data as ReportJsonResponse);
              }
            })
            .catch((err) => {
              markFailed(err instanceof Error ? err.message : 'report_fetch_failed');
            });
          break;
        }
        case 'failed':
          markFailed(evt.message ?? evt.error_code);
          break;
        case 'error':
          markFailed(evt.message ?? evt.code);
          break;
      }
    },
    [
      upsertAgent,
      recordConflict,
      recordDegraded,
      markCompleted,
      markFailed,
      setReport,
    ],
  );

  const wsUrl = jobId ? buildWsUrl(`/ws/progress/${jobId}`) : null;
  const wsEnabled = Boolean(jobId) && (status === 'queued' || status === 'running');
  const { connected, retries } = useWebSocket({
    url: wsUrl,
    onEvent: handleEvent,
    enabled: wsEnabled,
  });

  const submit = useCallback(
    async (input: AnalyzeRequest) => {
      try {
        const res = await startAnalysis(input);
        startJob(res.job_id);
      } catch (err) {
        markFailed(err instanceof Error ? err.message : 'submit_failed');
      }
    },
    [startJob, markFailed],
  );

  return { submit, reset, wsConnected: connected, wsRetries: retries };
}
