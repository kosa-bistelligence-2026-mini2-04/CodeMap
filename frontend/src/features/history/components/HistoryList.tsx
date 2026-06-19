"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RefreshCw, CheckCircle2, XCircle, Clock, Github, FolderOpen } from "lucide-react";
import type { RepoSource } from "@/features/repository/components/RepoInput";
import { useApp } from "@/common/contexts/AppContext";
import { fetchAnalysisHistory } from "@/features/analysis/api/api";

interface AnalysisRow {
  job_id: string;
  source: RepoSource;
  path: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: number;
  completed_at: number | null;
  total_pipeline_ms: number | null;
  error_message: string | null;
  model_used: string | null;
  force_refresh: boolean;
}

export interface HistoryListProps {
  onSelect: (jobId: string) => void;
  activeJobId?: string | null;
  refreshToken?: number;
}

function shortenPath(p: string, maxLen = 32): string {
  const normalized = p.replace(/\\/g, "/");
  if (normalized.length <= maxLen) return normalized;
  return "..." + normalized.slice(-(maxLen - 3));
}

function formatRelativeTime(unixSeconds: number): string {
  const delta = Date.now() / 1000 - unixSeconds;
  if (delta < 60) return "Just now";
  if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.floor(delta / 3600)}h ago`;
  if (delta < 604800) return `${Math.floor(delta / 86400)}d ago`;
  return new Date(unixSeconds * 1000).toLocaleDateString();
}

function toUnixSeconds(value: string): number {
  const timestamp = new Date(value).getTime();
  return Number.isNaN(timestamp) ? Date.now() / 1000 : timestamp / 1000;
}

/**
 * 백엔드 status 값을 프론트 STATUS_CONFIG 키(lowercase)로 정규화합니다.
 * 백엔드 계약은 lowercase이지만, 혹여 DB 내부 값(IN_PROGRESS/COMPLETED/FAILED)이
 * 그대로 전달되더라도 런타임 에러 없이 처리할 수 있도록 방어합니다.
 */
function normalizeStatus(status: string): AnalysisRow["status"] {
  const STATUS_NORMALIZE: Record<string, AnalysisRow["status"]> = {
    IN_PROGRESS: "running",
    COMPLETED: "completed",
    FAILED: "failed",
    QUEUED: "queued",
  };
  const normalized = STATUS_NORMALIZE[status];
  const valid = ["queued", "running", "completed", "failed"] as const;
  if (normalized) return normalized;
  if ((valid as readonly string[]).includes(status)) return status as AnalysisRow["status"];
  return "failed"; // 알 수 없는 상태는 failed로 안전하게 처리
}

export function HistoryList({ onSelect, activeJobId, refreshToken = 0 }: HistoryListProps) {
  const [items, setItems] = useState<AnalysisRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { theme, t } = useApp();
  const isDark = theme === "dark";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchAnalysisHistory(1, 30);
      setItems(response.data.jobs.map((job) => {
        const normalizedStatus = normalizeStatus(job.status);
        return {
          job_id: job.jobId,
          source: job.repoUrl.startsWith("https://") ? "github" : "local",
          path: job.repoUrl,
          status: normalizedStatus,
          created_at: toUnixSeconds(job.createdAt),
          completed_at: normalizedStatus === "completed" ? toUnixSeconds(job.updatedAt) : null,
          total_pipeline_ms: null,
          error_message: job.errorMessage,
          model_used: null,
          force_refresh: false,
        };
      }));
    } catch (requestError) {
      setItems([]);
      setError(requestError instanceof Error ? requestError.message : t.historyList.loadFailed);
    } finally {
      setLoading(false);
    }
  }, [t.historyList.loadFailed]);

  useEffect(() => {
    queueMicrotask(() => void load());
  }, [load, refreshToken]);

  const STATUS_CONFIG: Record<AnalysisRow["status"], { color: string; icon: typeof CheckCircle2; label: string }> = {
    queued: { color: "text-zinc-500 bg-zinc-500/10 border-zinc-500/30", icon: Clock, label: t.historyList.statusRunning },
    running: { color: "text-blue-500 bg-blue-500/10 border-blue-500/30", icon: RefreshCw, label: t.historyList.statusRunning },
    completed: { color: "text-green-500 bg-green-500/10 border-green-500/30", icon: CheckCircle2, label: t.historyList.statusDone },
    failed: { color: "text-red-500 bg-red-500/10 border-red-500/30", icon: XCircle, label: t.historyList.statusFailed },
  };

  const containerClass = isDark ? "bg-zinc-900/60 border-zinc-800" : "bg-white border-zinc-200 shadow-sm";
  const headerBorderClass = isDark ? "border-zinc-800" : "border-zinc-200";
  const titleClass = isDark ? "text-white" : "text-zinc-900";
  const refreshBtnClass = isDark ? "text-zinc-500 hover:text-white" : "text-zinc-400 hover:text-zinc-900";
  const itemHoverClass = isDark ? "hover:bg-zinc-800/40" : "hover:bg-zinc-50";
  const activeItemClass = isDark ? "bg-zinc-800/70 border-l-blue-500" : "bg-blue-50 border-l-blue-500";
  const pathClass = isDark ? "text-zinc-200" : "text-zinc-700";
  const timeClass = isDark ? "text-zinc-600" : "text-zinc-400";
  const dividerClass = isDark ? "divide-zinc-800/60" : "divide-zinc-100";

  return (
    <div className={`border rounded-2xl backdrop-blur-sm overflow-hidden transition-colors ${containerClass}`}>
      <div className={`flex items-center justify-between border-b px-4 py-3 transition-colors ${headerBorderClass}`}>
        <div className="flex items-center gap-2">
          <Clock className={`w-3.5 h-3.5 ${isDark ? "text-zinc-500" : "text-zinc-400"}`} />
          <h3 className={`text-xs font-semibold ${titleClass}`}>{t.historyList.title}</h3>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className={`text-[11px] font-medium disabled:opacity-40 transition-colors flex items-center gap-1 ${refreshBtnClass}`}
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          {loading ? t.historyList.loading : t.historyList.refresh}
        </button>
      </div>

      <div>
        {error && (
          <p className="px-4 py-3 text-[11px] text-red-400 font-medium">{t.historyList.loadFailed} {error}</p>
        )}
        {items.length === 0 && !loading && !error && (
          <div className="px-4 py-8 text-center">
            <p className={`text-[11px] ${isDark ? "text-zinc-600" : "text-zinc-500"}`}>{t.historyList.empty}</p>
            <p className={`text-[10px] mt-1 ${isDark ? "text-zinc-700" : "text-zinc-400"}`}>{t.historyList.emptyHint}</p>
          </div>
        )}

        <ul className={`max-h-[400px] overflow-y-auto divide-y transition-colors ${dividerClass}`}>
          <AnimatePresence initial={false}>
            {items.map((it) => {
              const cfg = STATUS_CONFIG[it.status];
              const StatusIcon = cfg.icon;
              const isGithub = it.source === "github";
              const isActive = activeJobId === it.job_id;

              return (
                <motion.li
                  key={it.job_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(it.job_id)}
                    className={`block w-full px-4 py-3 text-left transition-all border-l-2 ${
                      isActive ? activeItemClass : `${itemHoverClass} border-l-transparent`
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5 min-w-0">
                        {isGithub ? (
                          <Github className={`w-3 h-3 shrink-0 ${isDark ? "text-zinc-500" : "text-zinc-400"}`} />
                        ) : (
                          <FolderOpen className={`w-3 h-3 shrink-0 ${isDark ? "text-zinc-500" : "text-zinc-400"}`} />
                        )}
                        <span className={`truncate text-[11px] font-semibold ${pathClass}`} title={it.path}>
                          {shortenPath(it.path)}
                        </span>
                      </div>
                      <span className={`shrink-0 flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${cfg.color}`}>
                        <StatusIcon className={`w-2.5 h-2.5 ${it.status === "running" ? "animate-spin" : ""}`} />
                        {cfg.label}
                      </span>
                    </div>
                    <div className={`flex items-center justify-between text-[10px] pl-4 ${timeClass}`}>
                      <span>{formatRelativeTime(it.created_at)}</span>
                      <div className="flex items-center gap-2">
                        {it.model_used && <span className={isDark ? "text-zinc-700" : "text-zinc-500"}>{it.model_used}</span>}
                        {it.total_pipeline_ms != null && (
                          <span className={isDark ? "text-zinc-600" : "text-zinc-400"}>{(it.total_pipeline_ms / 1000).toFixed(1)}s</span>
                        )}
                      </div>
                    </div>
                  </button>
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ul>
      </div>
    </div>
  );
}
