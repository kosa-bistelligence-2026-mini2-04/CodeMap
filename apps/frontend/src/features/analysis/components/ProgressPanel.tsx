"use client";

import { memo } from "react";
import { motion } from "framer-motion";
import type { AgentName, AgentRuntimeStatus } from "@/common/types/contracts";
import { useApp } from "@/common/contexts/AppContext";

export interface ProgressPanelProps {
  jobId: string;
  agents: Record<AgentName, AgentRuntimeStatus>;
  wsConnected: boolean;
  wsRetries: number;
  onRetry?: (name: AgentName) => void;
}

const AGENT_NAMES: AgentName[] = [
  "static_analyzer",
  "behavior_inferer",
  "community_assessor",
  "reporter",
];

const AGENT_ICONS: Record<AgentName, string> = {
  static_analyzer: "⟁",
  behavior_inferer: "◈",
  community_assessor: "◉",
  reporter: "◎",
};

function clampProgress(p: number): number {
  return Math.min(100, Math.max(0, p));
}

function formatDurationMs(ms: number | undefined | null): string {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

interface AgentStatusCardProps {
  agent: AgentRuntimeStatus;
  onRetry?: (name: AgentName) => void;
  index: number;
  isDark: boolean;
  t: any;
}

const AgentStatusCard = memo(function AgentStatusCardImpl({
  agent,
  onRetry,
  index,
  isDark,
  t,
}: AgentStatusCardProps) {
  const progress = clampProgress(agent.progress);
  const canRetry = agent.status === "failed" && agent.name === "behavior_inferer";

  const STATUS_CONFIG = {
    pending: {
      border: isDark ? "border-zinc-800" : "border-zinc-200",
      bg: isDark ? "bg-zinc-900/30" : "bg-zinc-50",
      bar: isDark ? "bg-zinc-700" : "bg-zinc-300",
      label: isDark ? "text-zinc-600" : "text-zinc-500",
      text: t.progressPanel.statusPending,
    },
    running: {
      border: isDark ? "border-blue-500/40" : "border-blue-300",
      bg: isDark ? "bg-blue-500/5" : "bg-blue-50",
      bar: "bg-blue-500",
      label: isDark ? "text-blue-400" : "text-blue-600",
      text: t.progressPanel.statusRunning,
    },
    completed: {
      border: isDark ? "border-green-500/40" : "border-green-300",
      bg: isDark ? "bg-green-500/5" : "bg-green-50",
      bar: "bg-green-500",
      label: isDark ? "text-green-400" : "text-green-600",
      text: t.progressPanel.statusDone,
    },
    failed: {
      border: isDark ? "border-red-500/40" : "border-red-300",
      bg: isDark ? "bg-red-500/5" : "bg-red-50",
      bar: "bg-red-500",
      label: isDark ? "text-red-400" : "text-red-600",
      text: t.progressPanel.statusFailed,
    },
    degraded: {
      border: isDark ? "border-amber-500/40" : "border-amber-300",
      bg: isDark ? "bg-amber-500/5" : "bg-amber-50",
      bar: "bg-amber-500",
      label: isDark ? "text-amber-400" : "text-amber-600",
      text: t.progressPanel.statusDegraded,
    },
  } as const;

  const cfg = STATUS_CONFIG[agent.status];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07 }}
      className={`border rounded-xl p-3.5 transition-colors ${cfg.border} ${cfg.bg}`}
    >
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <span className={`font-mono text-xs ${cfg.label}`}>{AGENT_ICONS[agent.name]}</span>
          <span className={`text-xs font-semibold ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>
            {t.progressPanel.agents[agent.name as keyof typeof t.progressPanel.agents]}
          </span>
        </div>
        <span
          className={`text-[9px] font-bold uppercase tracking-wider ${cfg.label}`}
          aria-live="polite"
        >
          {cfg.text}
        </span>
      </div>

      {/* Progress Bar */}
      <div
        className={`h-1 w-full overflow-hidden rounded-full ${isDark ? "bg-zinc-800" : "bg-zinc-200"}`}
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${t.progressPanel.agents[agent.name as keyof typeof t.progressPanel.agents]} progress`}
      >
        <motion.div
          className={`h-full ${cfg.bar} ${agent.status === "running" ? "relative" : ""}`}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>

      <div className={`flex items-center justify-between mt-2 text-[10px] ${isDark ? "text-zinc-600" : "text-zinc-500"}`}>
        <span>{progress}%</span>
        {formatDurationMs(agent.duration_ms) && (
          <span>{formatDurationMs(agent.duration_ms)}</span>
        )}
      </div>

      {agent.stage_label && agent.status === "running" && (
        <p className={`animate-pulse mt-1.5 text-[10px] italic ${isDark ? "text-zinc-500" : "text-zinc-500"}`}>
          {agent.stage_label}
        </p>
      )}

      {agent.message && (
        <p className={`mt-1.5 text-[10px] leading-normal line-clamp-2 ${isDark ? "text-zinc-500" : "text-zinc-600"}`}>
          {agent.message}
        </p>
      )}

      {canRetry && onRetry && (
        <button
          type="button"
          onClick={() => onRetry(agent.name)}
          className={`mt-3 py-1 px-3 border rounded-lg text-[10px] font-semibold transition-colors ${
            isDark ? "border-zinc-700 hover:border-white text-zinc-400 hover:text-white" : "border-zinc-300 hover:border-zinc-900 text-zinc-500 hover:text-zinc-900"
          }`}
        >
          {t.progressPanel.retry}
        </button>
      )}
    </motion.div>
  );
});

export function ProgressPanel({
  jobId,
  agents,
  wsConnected,
  wsRetries,
  onRetry,
}: ProgressPanelProps) {
  const { theme, t } = useApp();
  const isDark = theme === "dark";

  return (
    <div className={`border rounded-2xl p-5 backdrop-blur-sm space-y-4 transition-colors ${
      isDark ? "bg-zinc-900/60 border-zinc-800" : "bg-white border-zinc-200 shadow-sm"
    }`}>
      <div className={`flex items-center justify-between border-b pb-3 transition-colors ${
        isDark ? "border-zinc-800" : "border-zinc-200"
      }`}>
        <div>
          <h3 className={`text-xs font-semibold ${isDark ? "text-white" : "text-zinc-900"}`}>{t.progressPanel.title}</h3>
          <p className={`text-[10px] mt-0.5 truncate max-w-[200px] font-mono ${isDark ? "text-zinc-600" : "text-zinc-400"}`} title={jobId}>
            {jobId.slice(0, 16)}...
          </p>
        </div>
        <span
          className={`text-[9px] font-bold uppercase tracking-wider px-2 py-1 rounded-lg border ${
            wsConnected
              ? isDark ? "text-green-400 bg-green-500/10 border-green-500/30" : "text-green-700 bg-green-50 border-green-200"
              : wsRetries > 0
              ? isDark ? "text-amber-400 bg-amber-500/10 border-amber-500/30 animate-pulse" : "text-amber-700 bg-amber-50 border-amber-200 animate-pulse"
              : isDark ? "text-zinc-600 bg-zinc-800 border-zinc-700" : "text-zinc-500 bg-zinc-100 border-zinc-200"
          }`}
          aria-live="polite"
        >
          {wsConnected
            ? `● ${t.progressPanel.wsLive}`
            : wsRetries > 0
            ? `${t.progressPanel.wsReconnecting} (${wsRetries}/5)`
            : t.progressPanel.wsDisconnected}
        </span>
      </div>

      <div className="space-y-2.5">
        {AGENT_NAMES.map((name, i) => (
          <AgentStatusCard key={name} agent={agents[name]} onRetry={onRetry} index={i} isDark={isDark} t={t} />
        ))}
      </div>
    </div>
  );
}
