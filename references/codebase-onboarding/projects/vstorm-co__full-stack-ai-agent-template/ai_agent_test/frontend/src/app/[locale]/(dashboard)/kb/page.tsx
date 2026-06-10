"use client";

import { useEffect, useState } from "react";
import { Database, Plus } from "lucide-react";

import { CreateKBDialog, KBList } from "@/components/kb";
import { EmptyState, LoadingState } from "@/components/states";
import { useKnowledgeBases } from "@/hooks";

export default function KBPage() {
  const { kbs, isLoading, fetchKBs, deleteKB } = useKnowledgeBases();
  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    fetchKBs();
  }, [fetchKBs]);

  const counts = {
    total: kbs.length,
    personal: kbs.filter((k) => k.scope === "personal").length,
    org: kbs.filter((k) => k.scope === "org").length,
    app: kbs.filter((k) => k.scope === "app").length,
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      {/* HERO */}
      <header className="border-foreground/10 bg-foreground/[0.02] relative isolate overflow-hidden rounded-3xl border p-7 sm:p-9">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 -right-24 -z-10 h-[340px] w-[340px] rounded-full blur-3xl"
          style={{
            background:
              "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.26), transparent 65%)",
          }}
        />
        <div
          aria-hidden
          className="bg-dots pointer-events-none absolute inset-0 -z-10 opacity-50"
        />

        <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          Knowledge bases
        </p>
        <h1 className="font-display text-foreground mt-2 text-3xl leading-[1.05] font-bold tracking-tight sm:text-4xl [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
          Documents your assistant <em>can use.</em>
        </h1>
        <p className="text-foreground/65 mt-4 max-w-xl text-sm">
          Group related documents into a base. Open one to upload files, then toggle in chat which
          ones the agent should search.
        </p>

        {/* Stats row */}
        {counts.total > 0 && (
          <div className="text-foreground/55 mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-[11px] tracking-wider uppercase">
            <StatPill value={counts.total} label="bases" />
            {counts.personal > 0 && <StatPill value={counts.personal} label="personal" />}
            {counts.org > 0 && <StatPill value={counts.org} label="org" />}
            {counts.app > 0 && <StatPill value={counts.app} label="app-wide" />}
          </div>
        )}

        <div className="mt-7">
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="bg-foreground text-background hover:bg-foreground/90 group inline-flex items-center gap-3 rounded-full py-2 pr-2 pl-5 text-sm font-medium transition-colors"
          >
            <span>New base</span>
            <span className="bg-brand text-brand-foreground flex h-8 w-8 items-center justify-center rounded-full transition-transform group-hover:rotate-90">
              <Plus className="h-4 w-4" />
            </span>
          </button>
        </div>
      </header>

      {/* Grid / empty / loading */}
      {isLoading ? (
        <LoadingState variant="skeleton-list" rows={4} />
      ) : kbs.length === 0 ? (
        <EmptyState
          icon={Database}
          title="No knowledge bases yet"
          description="Create one to give your assistant access to documents from collections."
          cta={{ label: "Create knowledge base", onClick: () => setCreateOpen(true) }}
        />
      ) : (
        <KBList kbs={kbs} onDelete={deleteKB} />
      )}

      <CreateKBDialog open={createOpen} onOpenChange={setCreateOpen} onCreated={() => fetchKBs()} />
    </div>
  );
}

function StatPill({ value, label }: { value: number; label: string }) {
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="text-foreground text-base tabular-nums">{value}</span>
      <span>{label}</span>
    </span>
  );
}
