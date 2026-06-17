"use client";

import { useMemo, useRef } from "react";
import { sanitizeReport } from "@/common/utils/sanitize";
import { HeatmapChart } from "./HeatmapChart";
import { AgentDurationsPanel } from "./AgentDurationsPanel";
import type { ReportJsonResponse } from "@/common/types/contracts";
import { useApp } from "@/common/contexts/AppContext";

export interface ReportViewerProps {
  report: ReportJsonResponse;
  htmlReport?: string | null;
  onLineClick?: (file: string, line: number) => void;
}

export function ReportViewer({
  report,
  htmlReport,
  onLineClick,
}: ReportViewerProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const { theme, t } = useApp();
  const isDark = theme === "dark";

  const safeHtml = useMemo(
    () => (htmlReport ? sanitizeReport(htmlReport) : ""),
    [htmlReport],
  );

  const cardClass = isDark ? "bg-zinc-900/40 border-zinc-800" : "bg-white border-zinc-200 shadow-sm";
  const titleClass = isDark ? "text-white" : "text-zinc-900";
  const descClass = isDark ? "text-zinc-400" : "text-zinc-600";
  const labelClass = isDark ? "text-zinc-500" : "text-zinc-400";
  const subCardClass = isDark ? "bg-zinc-800/50 border-zinc-700" : "bg-zinc-50 border-zinc-200";
  const metricValClass = isDark ? "text-white" : "text-zinc-900";
  const aiBadgeClass = isDark ? "bg-white text-black" : "bg-black text-white";
  const borderSepClass = isDark ? "border-zinc-800" : "border-zinc-200";
  const proseClass = isDark ? "prose-invert text-zinc-300" : "text-zinc-700";

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      {report.executive_summary && (
        <div className={`rounded-lg p-5 border ${cardClass} space-y-4`}>
          <div className={`flex items-center justify-between border-b pb-3 ${borderSepClass}`}>
            <h3 className={`text-sm font-semibold flex items-center gap-2 ${titleClass}`}>
              {t.reportViewer.execSummary}
              <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${aiBadgeClass}`}>
                {t.reportViewer.aiGenerated}
              </span>
            </h3>
            {report.health_score != null && (
              <span
                className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                  report.health_score >= 75
                    ? isDark ? "bg-green-500/10 border-green-500/30 text-green-400" : "bg-green-50 border-green-200 text-green-700"
                    : report.health_score >= 50
                    ? isDark ? "bg-yellow-500/10 border-yellow-500/30 text-yellow-400" : "bg-yellow-50 border-yellow-200 text-yellow-700"
                    : isDark ? "bg-red-500/10 border-red-500/30 text-red-400" : "bg-red-50 border-red-200 text-red-700"
                }`}
              >
                {t.reportViewer.healthScore}: {report.health_score}
              </span>
            )}
          </div>
          
          <div className="space-y-4">
            <p className={`text-xs leading-relaxed ${descClass}`}>
              {report.executive_summary}
            </p>

            {(report.key_strengths?.length || report.key_risks?.length) && (
              <div className="grid gap-4 md:grid-cols-2">
                {report.key_strengths && report.key_strengths.length > 0 && (
                  <div className={`p-3 rounded-md border ${subCardClass}`}>
                    <p className="mb-2 text-[9px] font-bold uppercase tracking-wider text-green-600">
                      {t.reportViewer.strengths}
                    </p>
                    <ul className={`space-y-1.5 text-xs ${descClass}`}>
                      {report.key_strengths.map((s) => (
                        <li key={s} className="flex items-start gap-1">
                          <span className="text-green-500 font-bold">•</span>
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {report.key_risks && report.key_risks.length > 0 && (
                  <div className={`p-3 rounded-md border ${subCardClass}`}>
                    <p className="mb-2 text-[9px] font-bold uppercase tracking-wider text-red-600">
                      {t.reportViewer.risks}
                    </p>
                    <ul className={`space-y-1.5 text-xs ${descClass}`}>
                      {report.key_risks.map((r) => (
                        <li key={r} className="flex items-start gap-1">
                          <span className="text-red-500 font-bold">•</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {report.summary_confidence != null && (
              <p className={`text-[10px] font-medium ${labelClass}`}>
                {t.reportViewer.confidence}: {(report.summary_confidence * 100).toFixed(0)}%
              </p>
            )}
          </div>
        </div>
      )}

      {/* Analysis Basic Info & Hotspots */}
      <div className={`rounded-lg p-5 border ${cardClass} space-y-4`}>
        <div>
          <h3 className={`text-sm font-semibold ${titleClass}`}>{t.reportViewer.analysisReport}</h3>
          <p className={`text-[10px] mt-1 ${labelClass}`}>
            {t.reportViewer.completedAt}: {report.completed_at ?? new Date().toISOString()} · {t.reportViewer.totalTime}:{" "}
            {(report.total_pipeline_ms / 1000).toFixed(1)}s
          </p>
        </div>

        {report.file_heatmap && Object.keys(report.file_heatmap).length > 0 && (
          <div className={`border-t pt-4 ${borderSepClass}`}>
            <HeatmapChart
              fileHeatmap={report.file_heatmap}
              onLineClick={onLineClick}
            />
          </div>
        )}
      </div>

      {/* Community Metrics */}
      {report.community && (
        <div className={`rounded-lg p-5 border ${cardClass} space-y-3`}>
          <h3 className={`text-sm font-semibold border-b pb-3 ${titleClass} ${borderSepClass}`}>
            {t.reportViewer.communityHealth}
          </h3>
          <div className={`grid gap-3 sm:grid-cols-3 text-xs ${descClass}`}>
            <div className={`p-3 rounded border ${subCardClass}`}>
              <span className={`block text-[10px] uppercase font-semibold ${labelClass}`}>{t.reportViewer.commitsPerWeek}</span>
              <span className={`text-sm font-bold ${metricValClass}`}>{report.community.commits_per_week.toFixed(1)}</span>
            </div>
            <div className={`p-3 rounded border ${subCardClass}`}>
              <span className={`block text-[10px] uppercase font-semibold ${labelClass}`}>{t.reportViewer.contributors}</span>
              <span className={`text-sm font-bold ${metricValClass}`}>{report.community.unique_contributors}</span>
            </div>
            <div className={`p-3 rounded border ${subCardClass}`}>
              <span className={`block text-[10px] uppercase font-semibold ${labelClass}`}>{t.reportViewer.avgIssueResponse}</span>
              <span className={`text-sm font-bold ${metricValClass}`}>
                {report.community.avg_issue_response_hours != null
                  ? `${report.community.avg_issue_response_hours.toFixed(1)}h`
                  : "N/A"}
              </span>
            </div>
          </div>

          {report.community.is_degraded && report.community.degraded_reason && (
            <p className={`text-xs font-semibold rounded p-2.5 border ${
              isDark ? "text-amber-400 bg-amber-500/10 border-amber-500/30" : "text-amber-600 bg-amber-50 border-amber-200"
            }`}>
              {t.reportViewer.degraded}: {report.community.degraded_reason}
            </p>
          )}

          {report.community.llm_analysis && (
            <div className={`rounded border p-3 mt-3 ${subCardClass}`}>
              <p className={`mb-1 text-[9px] font-bold uppercase tracking-wider ${labelClass}`}>{t.reportViewer.llmInterpretation}</p>
              <p className={`text-xs leading-relaxed ${descClass}`}>{report.community.llm_analysis}</p>
            </div>
          )}

          {!report.community.is_degraded &&
            report.community.commits_per_week === 0 &&
            report.community.unique_contributors === 0 && (
              <p className={`text-xs rounded p-2.5 border ${
                isDark ? "text-amber-400 bg-amber-500/10 border-amber-500/30" : "text-amber-600 bg-amber-50 border-amber-200"
              }`}>
                {t.reportViewer.noRecentCommits}
              </p>
            )}
        </div>
      )}

      {/* Recommendations */}
      <div className={`rounded-lg p-5 border ${cardClass} space-y-4`}>
        <h3 className={`text-sm font-semibold border-b pb-3 ${titleClass} ${borderSepClass}`}>
          {t.reportViewer.recommendations}
        </h3>
        <div className="space-y-3">
          {report.recommendations.map((rec, idx) => (
            <div
              key={`${rec.title}-${idx}`}
              className={`rounded-md border p-4 space-y-2 transition-colors ${subCardClass} ${isDark ? "hover:border-zinc-500" : "hover:border-neutral-300"}`}
            >
              <div className="flex items-center justify-between">
                <h4 className={`font-semibold text-xs ${titleClass}`}>{rec.title}</h4>
                <span className={`text-[9px] font-bold uppercase tracking-wider border px-1.5 py-0.5 rounded ${labelClass} ${borderSepClass}`}>
                  {rec.priority}
                </span>
              </div>
              <p className={`text-xs leading-normal ${descClass}`}>{rec.detail}</p>
              {rec.affected_files.length > 0 && (
                <div className={`text-[10px] ${labelClass}`}>
                  <span className={`font-semibold ${descClass}`}>Affected Files: </span>
                  {rec.affected_files.join(", ")}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Multi-Agent Conflict Resolution */}
      {report.conflicts_resolved.length > 0 && (
        <div className={`rounded-lg p-5 border shadow-sm space-y-4 ${
          isDark ? "bg-amber-900/10 border-amber-900/30" : "bg-white border-amber-200"
        }`}>
          <div className={`flex items-center justify-between border-b pb-3 ${
            isDark ? "border-amber-900/50" : "border-amber-100"
          }`}>
            <h3 className={`text-sm font-semibold flex items-center gap-2 ${titleClass}`}>
              {t.reportViewer.conflictResolution}
              <span className={`rounded border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                isDark ? "bg-amber-500/10 border-amber-500/30 text-amber-400" : "bg-amber-100 border-amber-200 text-amber-800"
              }`}>
                {t.reportViewer.llmJudge}
              </span>
            </h3>
            <span className={`text-xs font-semibold ${labelClass}`}>
              {report.conflicts_resolved.length} {t.reportViewer.conflictsResolved}
            </span>
          </div>
          <p className={`text-[11px] leading-normal ${labelClass}`}>
            {t.reportViewer.conflictDesc}
          </p>

          <div className="space-y-4 mt-3">
            {report.conflicts_resolved.map((c) => (
              <div
                key={c.module}
                className={`rounded-md border p-4 space-y-3 ${
                  isDark ? "bg-zinc-900/50 border-zinc-800" : "bg-neutral-50/50 border-neutral-200"
                }`}
              >
                <p className={`font-bold text-xs ${titleClass}`}>
                  {c.module}
                </p>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className={`rounded border p-3 text-[11px] ${subCardClass}`}>
                    <p className={`mb-1 font-bold ${titleClass}`}>
                      {t.reportViewer.staticView}
                    </p>
                    <p className={`leading-relaxed ${descClass}`}>{c.static_view}</p>
                  </div>
                  <div className={`rounded border p-3 text-[11px] ${subCardClass}`}>
                    <p className={`mb-1 font-bold ${titleClass}`}>
                      {t.reportViewer.behaviorView}
                    </p>
                    <p className={`leading-relaxed ${descClass}`}>{c.behavior_view}</p>
                  </div>
                </div>
                <div className={`rounded border-l-2 p-3 text-xs leading-relaxed ${
                  isDark ? "border-l-green-500 bg-green-500/5 border-zinc-800 text-zinc-300" : "border-l-green-500 bg-green-50/30 border-green-200/50 text-neutral-800"
                }`}>
                  <p className={`mb-1 font-bold text-[10px] uppercase tracking-wider ${
                    isDark ? "text-green-400" : "text-green-800"
                  }`}>
                    {t.reportViewer.judgeDecision}
                  </p>
                  <p className="text-xs">{c.final_recommendation}</p>
                  {(c.judge_model || c.confidence != null || c.escalated) && (
                    <p className={`mt-2 text-[9px] font-medium border-t pt-1.5 flex gap-2 ${
                      isDark ? "text-zinc-500 border-zinc-800/50" : "text-neutral-400 border-green-200/20"
                    }`}>
                      {c.judge_model && <span>Model: {c.judge_model}</span>}
                      {c.confidence != null && <span>Confidence: {(c.confidence * 100).toFixed(0)}%</span>}
                      {c.escalated && <span className="font-semibold text-amber-500">{t.reportViewer.escalated}</span>}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hallucination Guardrail Telemetry */}
      {report.guardrail_telemetry && (
        <div className={`rounded-lg p-5 border ${cardClass} space-y-4`}>
          <div className={`border-b pb-3 ${borderSepClass}`}>
            <h3 className={`text-sm font-semibold flex items-center gap-2 ${titleClass}`}>
              {t.reportViewer.guardrail}
              <span className={`rounded border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                isDark ? "bg-zinc-800 border-zinc-700 text-zinc-400" : "bg-neutral-100 border-neutral-300 text-neutral-700"
              }`}>
                {t.reportViewer.guardrailBadge}
              </span>
            </h3>
            <p className={`mt-1 text-[11px] leading-normal ${labelClass}`}>
              {t.reportViewer.guardrailDesc}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs md:grid-cols-4">
            <div className={`rounded border p-3 ${subCardClass}`}>
              <p className={`font-semibold text-[10px] uppercase ${labelClass}`}>{t.reportViewer.regexBlocked}</p>
              <p className={`mt-1 text-base font-bold ${metricValClass}`}>
                {report.guardrail_telemetry.regex_blocked.length}
              </p>
            </div>
            <div className={`rounded border p-3 ${subCardClass}`}>
              <p className={`font-semibold text-[10px] uppercase ${labelClass}`}>{t.reportViewer.semanticFiltered}</p>
              <p className={`mt-1 text-base font-bold ${metricValClass}`}>
                {report.guardrail_telemetry.semantic_filtered.length}
              </p>
            </div>
            <div className={`rounded border p-3 ${subCardClass}`}>
              <p className={`font-semibold text-[10px] uppercase ${labelClass}`}>{t.reportViewer.regenerations}</p>
              <p className={`mt-1 text-base font-bold ${metricValClass}`}>
                {report.guardrail_telemetry.regenerate_count}
              </p>
            </div>
            <div className={`rounded border p-3 ${subCardClass}`}>
              <p className={`font-semibold text-[10px] uppercase ${labelClass}`}>{t.reportViewer.fallbackStatus}</p>
              <p
                className={`mt-1 text-base font-bold ${
                  report.guardrail_telemetry.fallback_triggered
                    ? "text-red-500"
                    : "text-green-500"
                }`}
              >
                {report.guardrail_telemetry.fallback_triggered ? t.reportViewer.fallbackTriggered : t.reportViewer.fallbackInactive}
              </p>
            </div>

            {(report.guardrail_telemetry.input_secrets_redacted ?? 0) > 0 && (
              <div className={`col-span-2 rounded border p-3 text-[11px] md:col-span-4 flex items-center gap-1.5 font-medium ${
                isDark ? "border-red-500/30 bg-red-500/10 text-red-400" : "border-red-200 bg-red-50/50 text-red-800"
              }`}>
                <span>⚠️ Input side sanitization: Redacted {report.guardrail_telemetry.input_secrets_redacted} secret(s).</span>
                {(report.guardrail_telemetry.input_injections_blocked ?? 0) > 0 && (
                  <span>Blocked {report.guardrail_telemetry.input_injections_blocked} prompt injection attempt(s).</span>
                )}
              </div>
            )}
            
            {report.guardrail_telemetry.self_check_warnings.length > 0 && (
              <div className={`col-span-2 rounded border p-3 text-[11px] md:col-span-4 font-medium ${
                isDark ? "border-yellow-500/30 bg-yellow-500/10 text-yellow-400" : "border-yellow-200 bg-yellow-50/50 text-yellow-800"
              }`}>
                ⚠️ Reporter Self-Check Warnings: {report.guardrail_telemetry.self_check_warnings.length} warning(s) flagged.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Agent Durations Panel */}
      {report.agent_durations && Object.keys(report.agent_durations).length > 0 && (
        <AgentDurationsPanel durations={report.agent_durations} />
      )}

      {/* Full Detailed Report */}
      {safeHtml && (
        <div className={`rounded-lg p-6 border space-y-4 ${cardClass}`}>
          <h3 className={`text-sm font-semibold border-b pb-3 ${titleClass} ${borderSepClass}`}>
            {t.reportViewer.fullReport}
          </h3>
          <div
            ref={rootRef}
            className={`prose max-w-none text-xs leading-relaxed space-y-4 ${proseClass}`}
            dangerouslySetInnerHTML={{ __html: safeHtml }}
          />
        </div>
      )}
    </div>
  );
}
