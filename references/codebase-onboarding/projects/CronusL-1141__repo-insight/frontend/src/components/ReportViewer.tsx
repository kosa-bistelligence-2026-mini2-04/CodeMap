import { useEffect, useMemo, useRef } from 'react';
import parse from 'html-react-parser';
import { sanitizeReport } from '@/lib/sanitize';
import { HeatmapChart } from './HeatmapChart';
import { AgentDurationsPanel } from './AgentDurationsPanel';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import type { ReportJsonResponse } from '@/types/contracts';

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

  const safeHtml = useMemo(
    () => (htmlReport ? sanitizeReport(htmlReport) : ''),
    [htmlReport],
  );

  // Mount ECharts placeholders inside the sanitized HTML, if the backend
  // included any data-echarts-config nodes.
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const placeholders = root.querySelectorAll<HTMLDivElement>(
      '[data-echarts-config]',
    );
    if (placeholders.length === 0) return;

    let disposed = false;
    const instances: Array<{ dispose: () => void }> = [];

    void import('echarts').then((echarts) => {
      if (disposed) return;
      placeholders.forEach((el) => {
        const raw = el.getAttribute('data-echarts-config');
        if (!raw) return;
        try {
          const option = JSON.parse(raw);
          const chart = echarts.init(el);
          chart.setOption(option);
          instances.push(chart);
        } catch {
          // invalid embedded config — leave the placeholder untouched
        }
      });
    });

    return () => {
      disposed = true;
      instances.forEach((c) => c.dispose());
    };
  }, [safeHtml]);

  return (
    <div className="space-y-6">
      {report.executive_summary && (
        <Card className="border-primary/40 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2">
                执行摘要
                <span className="rounded bg-primary/10 px-2 py-0.5 text-[10px] font-normal text-primary">
                  LLM 生成
                </span>
              </span>
              {report.health_score != null && (
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    report.health_score >= 75
                      ? 'bg-green-100 text-green-700'
                      : report.health_score >= 50
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-red-100 text-red-700'
                  }`}
                >
                  健康度 {report.health_score}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm leading-relaxed text-foreground/90">
              {report.executive_summary}
            </p>
            {(report.key_strengths?.length || report.key_risks?.length) && (
              <div className="grid gap-3 md:grid-cols-2">
                {report.key_strengths && report.key_strengths.length > 0 && (
                  <div>
                    <p className="mb-1 text-[10px] uppercase tracking-wider text-green-700">
                      优势
                    </p>
                    <ul className="space-y-1 text-xs">
                      {report.key_strengths.map((s) => (
                        <li key={s} className="flex items-start gap-1">
                          <span className="text-green-600">+</span>
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {report.key_risks && report.key_risks.length > 0 && (
                  <div>
                    <p className="mb-1 text-[10px] uppercase tracking-wider text-red-700">
                      风险
                    </p>
                    <ul className="space-y-1 text-xs">
                      {report.key_risks.map((r) => (
                        <li key={r} className="flex items-start gap-1">
                          <span className="text-red-600">!</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            {report.summary_confidence != null && (
              <p className="text-[10px] text-muted-foreground">
                LLM 置信度：{(report.summary_confidence * 100).toFixed(0)}%
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>分析报告</CardTitle>
          <p className="text-xs text-muted-foreground">
            生成时间: {report.completed_at ?? new Date().toISOString()} · 总耗时:{' '}
            {(report.total_pipeline_ms / 1000).toFixed(1)} s
          </p>
        </CardHeader>
        <CardContent>
          {report.file_heatmap && Object.keys(report.file_heatmap).length > 0 && (
            <HeatmapChart
              fileHeatmap={report.file_heatmap}
              onLineClick={onLineClick}
            />
          )}
        </CardContent>
      </Card>

      {report.community && (
        <Card>
          <CardHeader>
            <CardTitle>社区健康</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              每周提交: {report.community.commits_per_week.toFixed(1)} · 贡献者:{' '}
              {report.community.unique_contributors}
            </p>
            {report.community.avg_issue_response_hours != null && (
              <p className="text-muted-foreground">
                Issue 平均响应: {report.community.avg_issue_response_hours.toFixed(1)} h
              </p>
            )}
            {report.community.is_degraded && report.community.degraded_reason && (
              <p className="text-xs text-warning">
                降级: {report.community.degraded_reason}
              </p>
            )}
            {report.community.llm_analysis && (
              <div className="mt-2 rounded border-l-2 border-primary/40 bg-muted/30 p-2">
                <p className="mb-1 text-[10px] uppercase text-primary">LLM 解读</p>
                <p className="text-xs leading-relaxed">{report.community.llm_analysis}</p>
              </div>
            )}
            {/* U-4 fix: surface warning when community data is all-zero (non-degraded but empty) */}
            {!report.community.is_degraded &&
              report.community.commits_per_week === 0 &&
              report.community.unique_contributors === 0 && (
                <p className="text-xs text-warning">
                  近 30 天无提交记录或 git 历史为空，指标无统计意义
                </p>
              )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>改进建议</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {report.recommendations.map((rec, idx) => (
            <div
              key={`${rec.title}-${idx}`}
              className="rounded-md border border-border p-3"
            >
              <div className="flex items-center justify-between">
                <h4 className="font-medium">{rec.title}</h4>
                <span className="text-xs uppercase text-muted-foreground">
                  {rec.priority}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{rec.detail}</p>
              {rec.affected_files.length > 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  影响文件: {rec.affected_files.join(', ')}
                </p>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      {report.conflicts_resolved.length > 0 && (
        <Card className="border-orange-300">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              多 Agent 冲突消解
              <span className="rounded bg-orange-100 px-2 py-0.5 text-[10px] font-normal text-orange-700">
                LLM 判官
              </span>
              <span className="ml-auto text-xs text-muted-foreground">
                {report.conflicts_resolved.length} 处冲突
              </span>
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              StaticAnalyzer 与 BehaviorInferer 对同一模块判断不一致时，由 LLM 判官做风险-价值权衡
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {report.conflicts_resolved.map((c) => (
              <div
                key={c.module}
                className="rounded-md border border-orange-300 bg-orange-50 p-3 text-sm dark:bg-orange-950/20"
              >
                <p className="font-semibold text-orange-900 dark:text-orange-200">
                  {c.module}
                </p>
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  <div className="rounded border border-blue-200 bg-blue-50 p-2 text-xs dark:bg-blue-950/20">
                    <p className="mb-1 font-semibold text-blue-700 dark:text-blue-300">
                      静态视图（StaticAnalyzer）
                    </p>
                    <p className="text-muted-foreground">{c.static_view}</p>
                  </div>
                  <div className="rounded border border-purple-200 bg-purple-50 p-2 text-xs dark:bg-purple-950/20">
                    <p className="mb-1 font-semibold text-purple-700 dark:text-purple-300">
                      行为视图（BehaviorInferer）
                    </p>
                    <p className="text-muted-foreground">{c.behavior_view}</p>
                  </div>
                </div>
                <div className="mt-2 rounded border-l-2 border-green-500 bg-green-50 p-2 text-xs dark:bg-green-950/20">
                  <p className="mb-1 font-semibold text-green-700 dark:text-green-300">
                    判官决策
                  </p>
                  <p>{c.final_recommendation}</p>
                  {(c.judge_model || c.confidence != null || c.escalated) && (
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      {c.judge_model && <>模型: {c.judge_model} · </>}
                      {c.confidence != null && <>置信度: {(c.confidence * 100).toFixed(0)}% · </>}
                      {c.escalated && <>已升级到高级判官</>}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {report.guardrail_telemetry && (
        <Card className="border-amber-300">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              幻觉防护链
              <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-normal text-amber-700">
                Guardrail
              </span>
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              双层过滤（正则 + 语义相似度）对 BehaviorInferer 的 LLM 输出拦截幻觉
            </p>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3 text-xs md:grid-cols-4">
              <div className="rounded border border-border p-2">
                <p className="text-muted-foreground">正则拦截</p>
                <p className="mt-1 text-lg font-bold">
                  {report.guardrail_telemetry.regex_blocked.length}
                </p>
              </div>
              <div className="rounded border border-border p-2">
                <p className="text-muted-foreground">语义过滤</p>
                <p className="mt-1 text-lg font-bold">
                  {report.guardrail_telemetry.semantic_filtered.length}
                </p>
              </div>
              <div className="rounded border border-border p-2">
                <p className="text-muted-foreground">重生成次数</p>
                <p className="mt-1 text-lg font-bold">
                  {report.guardrail_telemetry.regenerate_count}
                </p>
              </div>
              <div className="rounded border border-border p-2">
                <p className="text-muted-foreground">降级状态</p>
                <p
                  className={`mt-1 text-lg font-bold ${
                    report.guardrail_telemetry.fallback_triggered
                      ? 'text-red-600'
                      : 'text-green-600'
                  }`}
                >
                  {report.guardrail_telemetry.fallback_triggered ? '已触发' : '未触发'}
                </p>
              </div>
              {(report.guardrail_telemetry.input_secrets_redacted ?? 0) > 0 && (
                <div className="col-span-2 rounded border border-red-300 bg-red-50 p-2 dark:bg-red-950/20 md:col-span-4">
                  <p className="text-red-700 dark:text-red-300">
                    输入侧清理：密钥已打码 {report.guardrail_telemetry.input_secrets_redacted} 处
                    {(report.guardrail_telemetry.input_injections_blocked ?? 0) > 0 &&
                      ` · 注入尝试拦截 ${report.guardrail_telemetry.input_injections_blocked} 次`}
                  </p>
                </div>
              )}
              {report.guardrail_telemetry.self_check_warnings.length > 0 && (
                <div className="col-span-2 rounded border border-yellow-300 bg-yellow-50 p-2 dark:bg-yellow-950/20 md:col-span-4">
                  <p className="text-yellow-800 dark:text-yellow-200">
                    Reporter 自检警告：{report.guardrail_telemetry.self_check_warnings.length} 条
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {report.agent_durations && Object.keys(report.agent_durations).length > 0 && (
        <AgentDurationsPanel durations={report.agent_durations} />
      )}

      {safeHtml && (
        <Card>
          <CardHeader>
            <CardTitle>完整报告</CardTitle>
          </CardHeader>
          <CardContent>
            <div ref={rootRef} className="report-prose">
              {parse(safeHtml)}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
