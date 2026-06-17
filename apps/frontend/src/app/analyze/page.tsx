"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RepoInput, type RepoSource } from "@/features/repository/components/RepoInput";
import { ProgressPanel } from "@/features/analysis/components/ProgressPanel";
import { ReportViewer } from "@/features/analysis/components/ReportViewer";
import { HistoryList } from "@/features/history/components/HistoryList";
import { useWebSocket } from "@/common/hooks/useWebSocket";
import { startAnalysis, fetchReportJson, fetchReportHtml, buildWsUrl } from "@/features/analysis/api/api";
import type {
  AgentName,
  AgentRuntimeStatus,
  ReportJsonResponse,
  WsEvent,
} from "@/common/types/contracts";
import { Network, FileText, Clock } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";

function EmptyState() {
  const { theme, t } = useApp();
  const isDark = theme === "dark";
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`border rounded-2xl p-10 flex flex-col items-center justify-center text-center min-h-[50vh] transition-colors ${
        isDark ? "bg-zinc-900/40 border-zinc-800" : "bg-white border-zinc-200 shadow-sm"
      }`}
    >
      <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-5">
        <Network className="w-7 h-7 text-blue-400" />
      </div>
      <h3 className={`text-base font-semibold mb-2 ${isDark ? "text-white" : "text-zinc-900"}`}>{t.analyzePage.emptyTitle}</h3>
      <p className={`max-w-xs text-sm leading-relaxed ${isDark ? "text-zinc-500" : "text-zinc-500"}`}>
        {t.analyzePage.emptyDesc.split('"Start Analysis"')[0]}
        <span className={`font-semibold ${isDark ? "text-white" : "text-zinc-900"}`}>&ldquo;{t.repoInput.submit}&rdquo;</span>
        {t.analyzePage.emptyDesc.split('"Start Analysis"')[1] || " to run the multi-agent pipeline."}
      </p>
      <p className={`text-[11px] mt-5 leading-relaxed max-w-xs border-t pt-4 ${
        isDark ? "text-zinc-600 border-zinc-800" : "text-zinc-500 border-zinc-200"
      }`}>
        {t.analyzePage.emptyHint.split('"Analysis Records"')[0]}
        <span className={isDark ? "text-zinc-400" : "text-zinc-600"}>&ldquo;{t.historyList.title}&rdquo;</span>
        {t.analyzePage.emptyHint.split('"Analysis Records"')[1] || " list below."}
      </p>
    </motion.div>
  );
}

function LoadingSkeleton() {
  const { theme, t } = useApp();
  const isDark = theme === "dark";
  const pulseClass = isDark ? "bg-zinc-800" : "bg-zinc-200";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`border rounded-2xl p-8 flex flex-col gap-5 min-h-[50vh] transition-colors ${
        isDark ? "bg-zinc-900/40 border-zinc-800" : "bg-white border-zinc-200 shadow-sm"
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg animate-pulse ${pulseClass}`} />
        <div className={`h-4 w-44 rounded animate-pulse ${pulseClass}`} />
      </div>
      <div className={`h-3 w-64 rounded animate-pulse ${pulseClass}`} />
      <div className="mt-2 grid grid-cols-2 gap-4">
        <div className={`h-20 rounded-xl animate-pulse ${pulseClass}`} />
        <div className={`h-20 rounded-xl animate-pulse ${pulseClass}`} />
        <div className={`h-20 rounded-xl animate-pulse ${pulseClass}`} />
        <div className={`h-20 rounded-xl animate-pulse ${pulseClass}`} />
      </div>
      <div className={`mt-2 h-48 rounded-xl animate-pulse ${pulseClass}`} />
      <p className={`text-center text-[11px] font-semibold mt-auto ${isDark ? "text-zinc-600" : "text-zinc-400"}`}>
        {t.analyzePage.loadingMsg}
      </p>
    </motion.div>
  );
}

export default function AnalyzePage() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "queued" | "running" | "completed" | "failed">("idle");
  const [agents, setAgents] = useState<Record<AgentName, AgentRuntimeStatus>>({
    static_analyzer: { name: "static_analyzer", status: "pending", progress: 0 },
    behavior_inferer: { name: "behavior_inferer", status: "pending", progress: 0 },
    community_assessor: { name: "community_assessor", status: "pending", progress: 0 },
    reporter: { name: "reporter", status: "pending", progress: 0 },
  });
  const [report, setReport] = useState<ReportJsonResponse | null>(null);
  const [htmlReport, setHtmlReport] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [refreshToken, setRefreshToken] = useState(0);
  const [historicalJobId, setHistoricalJobId] = useState<string | null>(null);

  const { theme, t } = useApp();
  const isDark = theme === "dark";

  const running = status === "queued" || status === "running";

  // WebSocket Event Handler
  const handleEvent = useCallback((evt: WsEvent) => {
    switch (evt.type) {
      case "agent_status":
        setAgents((prev) => ({
          ...prev,
          [evt.agent]: {
            ...prev[evt.agent],
            status: evt.status,
            progress: evt.progress,
            stage_label: evt.stage_label,
          },
        }));
        setStatus((prev) => (prev === "queued" ? "running" : prev));
        break;
      case "agent_completed":
        setAgents((prev) => ({
          ...prev,
          [evt.agent]: {
            name: evt.agent,
            status: "completed",
            progress: 100,
            duration_ms: evt.duration_ms,
            message: evt.summary,
          },
        }));
        break;
      case "completed":
        setStatus("completed");
        fetchReportJson(evt.job_id)
          .then((data) => {
            if ("recommendations" in data) {
              setReport(data as ReportJsonResponse);
            }
          })
          .catch((err) => {
            setStatus("failed");
            setError(err.message || "Failed to fetch report data");
          });

        fetchReportHtml(evt.job_id)
          .then((html) => setHtmlReport(html))
          .catch(() => {});

        setRefreshToken((r) => r + 1);
        break;
      case "failed":
        setStatus("failed");
        setError(evt.message || evt.error_code);
        break;
      case "error":
        setStatus("failed");
        setError(evt.message || evt.code);
        break;
    }
  }, []);

  // WebSocket Hook
  const wsUrl = jobId ? buildWsUrl(`/ws/progress/${jobId}`) : null;
  const wsEnabled = Boolean(jobId) && (status === "queued" || status === "running");
  const { connected: wsConnected, retries: wsRetries } = useWebSocket({
    url: wsUrl,
    onEvent: handleEvent,
    enabled: wsEnabled,
  });

  // Submit new analysis job
  const submit = async (input: {
    source: RepoSource;
    path: string;
    force_refresh?: boolean;
    model?: string;
  }) => {
    setStatus("queued");
    setReport(null);
    setHtmlReport(null);
    setError(null);
    setHistoricalJobId(null);
    setAgents({
      static_analyzer: { name: "static_analyzer", status: "pending", progress: 0 },
      behavior_inferer: { name: "behavior_inferer", status: "pending", progress: 0 },
      community_assessor: { name: "community_assessor", status: "pending", progress: 0 },
      reporter: { name: "reporter", status: "pending", progress: 0 },
    });

    try {
      const res = await startAnalysis(input);
      setJobId(res.job_id);
    } catch (err: unknown) {
      setStatus("failed");
      setError(err instanceof Error ? err.message : "Analysis request failed.");
    }
  };

  // Load selected history item
  const loadHistorical = useCallback(async (clickedJobId: string) => {
    try {
      setStatus("completed");
      setError(null);

      const resp = await fetchReportJson(clickedJobId);
      if ("recommendations" in resp) {
        setReport(resp as ReportJsonResponse);
      } else {
        throw new Error("Report not completed yet.");
      }

      const html = await fetchReportHtml(clickedJobId).catch(() => null);
      setHtmlReport(html);
      setHistoricalJobId(clickedJobId);
    } catch (e) {
      alert(`Failed to load: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, []);

  // Detect URL search query params on mount
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const pathParam = params.get("path");
    const sourceParam = params.get("source") as RepoSource | null;

    if (pathParam) {
      void submit({
        path: pathParam,
        source: sourceParam || "local",
      });
    }
  }, []);

  const handleLineClick = (file: string, line: number) => {
    console.log(`Scroll to: ${file}:${line}`);
  };

  const pageBgClass = isDark ? "bg-[#09090b] text-white" : "bg-zinc-50 text-zinc-900";
  const headerBorderClass = isDark ? "border-zinc-800/60" : "border-zinc-200 bg-white";
  const headerTitleClass = isDark ? "text-white" : "text-zinc-900";
  const errorBoxClass = isDark ? "border-red-500/30 bg-red-500/10 text-red-400" : "border-red-300 bg-red-50 text-red-700";

  return (
    <div className={`min-h-screen transition-colors ${pageBgClass}`}>
      {/* Page header */}
      <div className={`border-b px-6 py-4 transition-colors ${headerBorderClass}`}>
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <h1 className={`text-sm font-semibold ${headerTitleClass}`}>{t.analyzePage.pageTitle}</h1>
          </div>
          {jobId && (
            <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-mono">
              <Clock className="w-3 h-3" />
              <span>Job: {jobId.slice(0, 8)}...</span>
              <span className={`px-1.5 py-0.5 rounded border font-bold uppercase tracking-wider ${
                status === "completed" ? "bg-green-500/10 border-green-500/30 text-green-400" :
                status === "running" ? "bg-blue-500/10 border-blue-500/30 text-blue-400" :
                status === "queued" ? "bg-yellow-500/10 border-yellow-500/30 text-yellow-400" :
                status === "failed" ? "bg-red-500/10 border-red-500/30 text-red-400" :
                "bg-zinc-800 border-zinc-700 text-zinc-500"
              }`}>
                {status}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main layout */}
      <main className="mx-auto max-w-7xl px-6 py-8 grid gap-6 lg:grid-cols-[380px_1fr]">
        {/* Sidebar */}
        <aside className="space-y-5">
          <RepoInput onSubmit={submit} disabled={running} />

          <AnimatePresence>
            {jobId && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <ProgressPanel
                  jobId={jobId}
                  agents={agents}
                  wsConnected={wsConnected}
                  wsRetries={wsRetries}
                />
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`rounded-xl border p-4 text-xs font-semibold leading-normal ${errorBoxClass}`}
              >
                ⚠ {error}
              </motion.div>
            )}
          </AnimatePresence>

          <HistoryList
            onSelect={loadHistorical}
            activeJobId={historicalJobId || jobId}
            refreshToken={refreshToken}
          />
        </aside>

        {/* Main Content Area */}
        <section className="min-h-[50vh]">
          <AnimatePresence mode="wait">
            {report ? (
              <motion.div
                key="report"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <ReportViewer
                  report={report}
                  htmlReport={htmlReport}
                  onLineClick={handleLineClick}
                />
              </motion.div>
            ) : running ? (
              <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <LoadingSkeleton />
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <EmptyState />
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </main>
    </div>
  );
}
