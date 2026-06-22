"use client";

import {
  Boxes,
  Braces,
  Database,
  Layers3,
  Play,
  Server,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";

interface StructureOverviewProps {
  primaryLanguage?: string;
  stack: string[];
  entrypoints: string[];
  onFileSelect: (file: string) => void;
}

function getStackIcon(name: string): LucideIcon {
  const normalized = name.toLowerCase();
  if (/postgres|mysql|mongo|redis|database|sql/.test(normalized)) return Database;
  if (/fastapi|django|express|spring|server/.test(normalized)) return Server;
  if (/react|next|vue|angular|svelte/.test(normalized)) return Layers3;
  if (/python|typescript|javascript|java|kotlin|go|rust/.test(normalized)) return Braces;
  return Boxes;
}

export function StructureOverview({
  primaryLanguage,
  stack,
  entrypoints,
  onFileSelect,
}: StructureOverviewProps) {
  const { theme, locale } = useApp();
  const isDark = theme === "dark";
  const isKo = locale === "ko";
  const technologies = [...new Set([primaryLanguage, ...stack].filter((item): item is string => Boolean(item)))];
  const card = isDark ? "border-zinc-800 bg-zinc-900/55" : "border-zinc-200 bg-white";
  const subCard = isDark ? "border-zinc-800 bg-zinc-950/45" : "border-zinc-200 bg-zinc-50";
  const muted = "text-zinc-500";

  return (
    <section className={`rounded-2xl border p-5 shadow-sm ${card}`} aria-labelledby="structure-overview-title">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 id="structure-overview-title" className="flex items-center gap-2 text-sm font-bold">
            <Workflow className="size-4 text-cyan-400" />
            {isKo ? "프로젝트 구조 개요" : "Project structure"}
          </h2>
          <p className={`mt-1 text-[10px] ${muted}`}>
            {isKo ? "탐지된 실행 기술과 코드 진입점을 함께 확인합니다." : "Detected runtime technologies and code entry points."}
          </p>
        </div>
        <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[8px] font-bold uppercase tracking-wider text-emerald-400">
          parsed
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className={`rounded-xl border p-4 ${subCard}`}>
          <p className={`mb-3 text-[9px] font-bold uppercase tracking-[0.16em] ${muted}`}>
            {isKo ? "기술 스택" : "Technology stack"}
          </p>
          {technologies.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {technologies.map((technology) => {
                const Icon = getStackIcon(technology);
                return (
                  <span
                    key={technology}
                    className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[10px] font-semibold ${
                      isDark ? "border-zinc-700 bg-zinc-900 text-zinc-300" : "border-zinc-200 bg-white text-zinc-700"
                    }`}
                  >
                    <Icon className="size-3.5 text-blue-400" />
                    {technology}
                  </span>
                );
              })}
            </div>
          ) : (
            <p className={`text-[10px] ${muted}`}>{isKo ? "탐지된 기술 스택이 없습니다." : "No technologies detected."}</p>
          )}
        </div>

        <div className={`rounded-xl border p-4 ${subCard}`}>
          <p className={`mb-3 text-[9px] font-bold uppercase tracking-[0.16em] ${muted}`}>
            {isKo ? "진입점" : "Entry points"}
          </p>
          {entrypoints.length > 0 ? (
            <ul className="space-y-1.5">
              {entrypoints.slice(0, 8).map((file) => (
                <li key={file}>
                  <button
                    type="button"
                    onClick={() => onFileSelect(file)}
                    title={file}
                    className={`group flex w-full items-center gap-2 rounded-lg border px-2.5 py-2 text-left transition ${
                      isDark
                        ? "border-emerald-500/10 bg-emerald-500/5 text-zinc-300 hover:border-emerald-500/30 hover:bg-emerald-500/10"
                        : "border-emerald-200 bg-emerald-50/60 text-zinc-700 hover:border-emerald-300 hover:bg-emerald-50"
                    }`}
                  >
                    <span className="flex size-5 shrink-0 items-center justify-center rounded-md bg-emerald-500/10">
                      <Play className="size-2.5 fill-emerald-400/20 text-emerald-400" />
                    </span>
                    <span className="min-w-0 flex-1 truncate font-mono text-[10px]">{file}</span>
                    <span className="text-[8px] font-bold uppercase tracking-wide text-emerald-500 opacity-70 transition group-hover:opacity-100">
                      entry
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className={`text-[10px] ${muted}`}>{isKo ? "탐지된 진입점이 없습니다." : "No entry points detected."}</p>
          )}
        </div>
      </div>
    </section>
  );
}
