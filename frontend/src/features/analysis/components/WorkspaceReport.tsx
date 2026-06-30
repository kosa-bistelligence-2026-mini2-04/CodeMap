"use client";

import {
  ArrowRight,
  Braces,
  CheckCircle2,
  CircleGauge,
  FileCode2,
  Files,
  GitBranch,
  MessageSquareText,
  ShieldAlert,
  Sparkles,
  TestTube2,
} from "lucide-react";
import type { WorkspaceReport as WorkspaceReportData } from "@/common/types/contracts";
import { useApp } from "@/common/contexts/AppContext";
import { StructureOverview } from "./StructureOverview";
import { DashboardCharts } from "./DashboardCharts";

interface WorkspaceReportProps {
  report: WorkspaceReportData;
  preview?: boolean;
  onAsk: (prompt: string, contextFile?: string) => void;
  onFileSelect: (file: string) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function WorkspaceReport({ report, preview, onAsk, onFileSelect }: WorkspaceReportProps) {
  const { theme } = useApp();
  const isDark = theme === "dark";
  const card = isDark ? "border-zinc-800 bg-zinc-900/55" : "border-zinc-200 bg-white";
  const muted = isDark ? "text-zinc-500" : "text-zinc-500";
  const maxLanguageLines = Math.max(...report.languages.map((item) => item.lines), 1);

  const metrics = [
    { label: "분석 파일", value: report.stats.files.toLocaleString(), icon: Files, color: "text-blue-400" },
    { label: "코드 라인", value: report.stats.lines.toLocaleString(), icon: Braces, color: "text-violet-400" },
    { label: "테스트 파일", value: report.stats.tests.toLocaleString(), icon: TestTube2, color: "text-emerald-400" },
    { label: "스냅샷", value: formatBytes(report.stats.bytes), icon: GitBranch, color: "text-amber-400" },
  ];

  return (
    <div className="mx-auto w-full max-w-5xl space-y-5 pb-12">
      <section className={`overflow-hidden rounded-2xl border shadow-sm ${card}`}>
        <div className="relative p-5 md:p-7">
          <div className="pointer-events-none absolute -right-20 -top-24 size-72 rounded-full bg-blue-500/10 blur-3xl" />
          <div className="relative flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 flex-1 max-w-2xl">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold text-emerald-400">
                  <CheckCircle2 className="size-3" /> 실제 스냅샷 분석 완료
                </span>
                {preview && (
                  <span className="rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-1 text-[10px] font-bold text-amber-400">
                    제품 미리보기 데이터
                  </span>
                )}
              </div>
              <h1 className="text-xl font-bold tracking-tight md:text-2xl">{report.repository.name}</h1>
              <p className={`mt-2 text-sm leading-6 ${muted}`}>{report.executive_summary}</p>
            </div>
            <div className={`flex min-w-40 items-center gap-3 rounded-2xl border p-3.5 ${isDark ? "border-zinc-800 bg-zinc-950/60" : "border-zinc-200 bg-zinc-50"}`}>
              <div className="relative flex size-12 items-center justify-center rounded-full bg-emerald-500/10">
                <CircleGauge className="size-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">구조 건강도</p>
                <p className="mt-0.5 text-xl font-bold">{report.health_score}<span className="text-xs font-medium text-zinc-600"> / 100</span></p>
              </div>
            </div>
          </div>
        </div>
        <div className={`grid grid-cols-2 border-t lg:grid-cols-4 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
          {metrics.map((metric, index) => {
            const Icon = metric.icon;
            return (
              <div key={metric.label} className={`flex items-center gap-3 px-4 py-3.5 ${index > 0 ? isDark ? "border-l border-zinc-800" : "border-l border-zinc-200" : ""}`}>
                <Icon className={`size-4 ${metric.color}`} />
                <div><p className="text-sm font-bold">{metric.value}</p><p className="text-[9px] font-semibold text-zinc-500">{metric.label}</p></div>
              </div>
            );
          })}
        </div>
      </section>

      <StructureOverview
        primaryLanguage={report.stats.primary_language}
        stack={report.stack}
        entrypoints={report.entrypoints}
        onFileSelect={onFileSelect}
      />

      {/* 새롭게 추가된 대시보드 시각화 컴포넌트 */}
      <DashboardCharts report={report} />

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <section className={`rounded-2xl border p-5 shadow-sm ${card}`}>
          <div className="mb-5 flex items-center justify-between">
            <div><h2 className="text-sm font-bold">언어 구성</h2><p className={`mt-0.5 text-[10px] ${muted}`}>실제 소스 라인 기준</p></div>
            <FileCode2 className="size-4 text-blue-400" />
          </div>
          <div className="space-y-3.5">
            {report.languages.slice(0, 6).map((language) => (
              <div key={language.name}>
                <div className="mb-1.5 flex justify-between text-[10px]"><span className="font-semibold">{language.name}</span><span className={muted}>{language.lines.toLocaleString()} lines</span></div>
                <div className={`h-1.5 overflow-hidden rounded-full ${isDark ? "bg-zinc-800" : "bg-zinc-100"}`}>
                  <div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400" style={{ width: `${Math.max(5, language.lines / maxLanguageLines * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className={`rounded-2xl border p-5 shadow-sm ${card}`}>
          <div className="mb-4 flex items-center justify-between">
            <div><h2 className="text-sm font-bold">추천 읽기 순서</h2><p className={`mt-0.5 text-[10px] ${muted}`}>진입점과 실행 구성을 우선 정렬</p></div>
            <ArrowRight className="size-4 text-violet-400" />
          </div>
          <div className="space-y-1.5">
            {(report.reading_order || report.entrypoints).slice(0, 6).map((file, index) => (
              <div key={file} className={`group flex items-center gap-1 rounded-lg pr-1 transition ${isDark ? "hover:bg-zinc-800/70" : "hover:bg-zinc-50"}`}>
                <button onClick={() => onFileSelect(file)} className="flex min-w-0 flex-1 items-center gap-2.5 px-2.5 py-2 text-left">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-md bg-violet-500/10 text-[9px] font-bold text-violet-400">{index + 1}</span>
                  <span className="min-w-0 flex-1 truncate font-mono text-[10px]">{file}</span>
                </button>
                <button onClick={() => onAsk(`${file}의 역할과 호출 흐름을 설명해줘`, file)} className="rounded-md p-1.5 text-zinc-600 opacity-0 transition hover:bg-blue-500/10 hover:text-blue-400 group-hover:opacity-100 focus:opacity-100" aria-label={`${file} 질문하기`} title="이 파일 질문하기">
                  <MessageSquareText className="size-3.5" />
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className={`rounded-2xl border p-5 shadow-sm ${card}`}>
          <div className="mb-4 flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /><h2 className="text-sm font-bold">확인된 강점</h2></div>
          <div className="space-y-3">
            {report.key_strengths.map((item) => <p key={item} className={`text-xs leading-5 ${muted}`}>• {item}</p>)}
          </div>
        </section>
        <section className={`rounded-2xl border p-5 shadow-sm ${card}`}>
          <div className="mb-4 flex items-center gap-2"><ShieldAlert className="size-4 text-amber-400" /><h2 className="text-sm font-bold">검토할 신호</h2></div>
          <div className="space-y-3">
            {report.key_risks.map((item) => <p key={item} className={`text-xs leading-5 ${muted}`}>• {item}</p>)}
          </div>
          <button onClick={() => onAsk("이 분석에서 우선 확인해야 할 위험 요소와 근거 파일을 알려줘")} className="mt-4 inline-flex items-center gap-1.5 text-[11px] font-semibold text-blue-400 hover:text-blue-300">
            채팅에서 근거 확인 <ArrowRight className="size-3" />
          </button>
        </section>
      </div>

      <section className={`rounded-2xl border p-5 shadow-sm ${card}`}>
        <div className="mb-4 flex items-center gap-2"><Sparkles className="size-4 text-blue-400" /><h2 className="text-sm font-bold">실행 권장사항</h2></div>
        <div className="grid gap-3 md:grid-cols-2">
          {report.recommendations.map((recommendation) => (
            <article key={recommendation.title} className={`rounded-xl border p-4 ${isDark ? "border-zinc-800 bg-zinc-950/35" : "border-zinc-200 bg-zinc-50"}`}>
              <div className="flex items-start justify-between gap-3"><h3 className="text-xs font-bold leading-5">{recommendation.title}</h3><span className="rounded-md bg-blue-500/10 px-1.5 py-0.5 text-[8px] font-bold uppercase text-blue-400">{recommendation.priority}</span></div>
              <p className={`mt-2 text-[11px] leading-5 ${muted}`}>{recommendation.detail}</p>
              <button onClick={() => onAsk(`${recommendation.title}을 실제 코드 기준으로 어떻게 진행하면 좋을지 알려줘`, recommendation.affected_files[0])} className="mt-3 inline-flex items-center gap-1.5 text-[10px] font-bold text-blue-400">
                이 권장사항 질문하기 <MessageSquareText className="size-3" />
              </button>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
