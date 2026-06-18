"use client";

import { ArrowUpRight, Github, Sparkles } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";
import { TRENDING_REPOSITORIES } from "@/features/landing/data/trendingRepos";

type TrendingReposProps = {
  onAnalyze: (url: string) => void;
};

export function TrendingRepos({ onAnalyze }: TrendingReposProps) {
  const { locale, t } = useApp();

  return (
    <section className="relative z-10 w-full border-t border-white/5 px-6 py-20">
      <div className="mx-auto max-w-7xl">
        <div className="mb-9 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <span className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-blue-500/20 bg-blue-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-blue-400">
              <Sparkles className="size-3" /> {t.trending.eyebrow}
            </span>
            <h2 className="text-3xl font-bold tracking-tight cm-text-primary md:text-4xl">
              {t.trending.title}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 cm-text-muted">
              {t.trending.subtitle}
            </p>
          </div>
          <p className="text-[11px] cm-text-faint">{t.trending.curatedNote}</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {TRENDING_REPOSITORIES.map((repo) => (
            <article
              key={repo.name}
              className="group flex min-h-48 flex-col rounded-2xl border p-4 transition-all duration-200 hover:-translate-y-1 hover:border-blue-500/40 cm-card"
            >
              <div className="flex items-center justify-between">
                <div className="flex size-9 items-center justify-center rounded-xl border border-white/10 bg-black/10">
                  <Github className="size-4 cm-text-muted" />
                </div>
                <ArrowUpRight className="size-4 opacity-0 transition-opacity group-hover:opacity-100 cm-text-faint" />
              </div>
              <h3 className="mt-4 truncate text-sm font-bold cm-text-primary">{repo.name}</h3>
              <p className="mt-2 line-clamp-3 text-xs leading-5 cm-text-muted">
                {repo.description[locale]}
              </p>
              <div className="mt-auto flex items-center justify-between gap-2 pt-4">
                <span className="flex min-w-0 items-center gap-1.5 truncate text-[10px] cm-text-faint">
                  <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: repo.accent }} />
                  {repo.language}
                </span>
                <button
                  type="button"
                  onClick={() => onAnalyze(repo.url)}
                  className="shrink-0 rounded-lg bg-blue-500/10 px-2.5 py-1.5 text-[10px] font-bold text-blue-400 transition-colors hover:bg-blue-500/20"
                  aria-label={`${repo.name} ${t.trending.analyze}`}
                >
                  {t.trending.analyze}
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
