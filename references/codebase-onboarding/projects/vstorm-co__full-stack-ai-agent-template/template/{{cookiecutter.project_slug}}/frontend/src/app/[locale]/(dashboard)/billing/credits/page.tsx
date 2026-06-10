"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  ArrowUpRight,
  Coins,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { toast } from "sonner";

import { PageHero } from "@/components/dashboard/page-hero";
import { LoadingState } from "@/components/states";
import { Button } from "@/components/ui";
import { useBilling, useCredits } from "@/hooks";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface UsageBucket {
  day: string;
  credits_charged: number;
}

interface UsageTimelineRead {
  buckets: UsageBucket[];
  days: number;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function humanizeType(t: string): string {
  return t.replace(/_/g, " ");
}

export default function CreditsPage() {
  const searchParams = useSearchParams();
  const { balance, transactions, isLoading, txLoading } = useCredits();
  const { startCheckout, isLoading: checkoutLoading } = useBilling();
  const [timeline, setTimeline] = useState<UsageBucket[] | null>(null);

  useEffect(() => {
    if (searchParams.get("topup") === "1") {
      toast.success("Credits added to your account!");
    }
  }, [searchParams]);

  useEffect(() => {
    apiClient
      .get<UsageTimelineRead>("/billing/me/credits/usage/timeline?days=30")
      .then((d) => setTimeline(d.buckets))
      .catch(() => setTimeline([]));
  }, []);

  const last7Total = useMemo(
    () => (timeline ?? []).slice(-7).reduce((a, b) => a + b.credits_charged, 0),
    [timeline],
  );
  const prior7Total = useMemo(
    () => (timeline ?? []).slice(-14, -7).reduce((a, b) => a + b.credits_charged, 0),
    [timeline],
  );
  const trendPct =
    prior7Total > 0 ? ((last7Total - prior7Total) / prior7Total) * 100 : last7Total > 0 ? 100 : 0;

  const sparkData = useMemo(
    () => (timeline ?? []).slice(-30).map((b, i) => ({ i, v: b.credits_charged })),
    [timeline],
  );

  const low = balance && balance.low_threshold > 0 && balance.balance < balance.low_threshold;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 pb-10">
      <div>
        <Link
          href="/billing"
          className="text-foreground/55 hover:text-foreground inline-flex items-center gap-1.5 font-mono text-[11px] tracking-wider uppercase"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to billing
        </Link>
      </div>

      <PageHero
        eyebrow="Credits"
        title={
          <>
            Balance &amp; <em>usage.</em>
          </>
        }
        description="Credits power AI completions, embeddings, and tool calls."
        actions={
          <Button
            onClick={() =>
              startCheckout({
                success_url: window.location.href + "?topup=1",
                cancel_url: window.location.href,
              })
            }
            disabled={checkoutLoading}
            className="rounded-full"
          >
            {checkoutLoading ? "Opening…" : "Top up"}
          </Button>
        }
      />

      {/* Balance card with sparkline */}
      <section
        className={cn(
          "relative overflow-hidden rounded-3xl border p-6 sm:p-8",
          low ? "border-destructive/30 bg-destructive/[0.04]" : "border-foreground/10 bg-card",
        )}
      >
        <div className="bg-brand/[0.06] pointer-events-none absolute -top-32 -right-32 h-72 w-72 rounded-full blur-[120px]" />
        <div className="relative grid gap-8 md:grid-cols-[1fr_1.4fr] md:items-center">
          <div>
            <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
              Current balance
            </p>
            {isLoading ? (
              <div className="bg-foreground/8 mt-3 h-12 w-40 animate-pulse rounded-md" />
            ) : (
              <p className="font-display text-foreground mt-2 text-5xl font-bold tracking-tight tabular-nums">
                {balance?.balance.toLocaleString() ?? "—"}
              </p>
            )}
            <p className="text-foreground/55 mt-2 text-sm">credits remaining</p>
            {low && balance && (
              <p className="text-destructive mt-3 inline-flex items-center gap-2 text-xs font-medium">
                <AlertCircle className="h-3.5 w-3.5" />
                Below alert threshold of {balance.low_threshold.toLocaleString()} credits.
              </p>
            )}
          </div>

          <div>
            <div className="flex items-baseline justify-between">
              <span className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
                Usage · last 30 days
              </span>
              {timeline && (
                <span
                  className={cn(
                    "inline-flex items-center gap-1 font-mono text-[11px] font-semibold",
                    trendPct > 0
                      ? "text-destructive"
                      : trendPct < 0
                        ? "text-brand"
                        : "text-foreground/55",
                  )}
                >
                  {trendPct > 0 ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : trendPct < 0 ? (
                    <TrendingDown className="h-3 w-3" />
                  ) : null}
                  {Math.abs(trendPct).toFixed(1)}% wk-over-wk
                </span>
              )}
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="font-display text-foreground text-2xl font-bold">
                {last7Total.toLocaleString()}
              </span>
              <span className="text-foreground/55 text-sm">credits · last 7 days</span>
            </div>
            <div className="mt-2 h-16 w-full">
              {!timeline ? (
                <div className="bg-foreground/8 h-full animate-pulse rounded-md" />
              ) : sparkData.length < 2 ? (
                <p className="text-foreground/45 text-xs">Not enough data yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={sparkData}>
                    <defs>
                      <linearGradient id="credits-spark" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--color-brand)" stopOpacity={0.45} />
                        <stop offset="100%" stopColor="var(--color-brand)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area
                      type="monotone"
                      dataKey="v"
                      stroke="var(--color-brand)"
                      strokeWidth={1.5}
                      fill="url(#credits-spark)"
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Transactions */}
      <section className="border-foreground/10 bg-card rounded-2xl border">
        <div className="border-foreground/10 flex items-center justify-between border-b px-6 py-5">
          <div>
            <h2 className="font-display text-foreground text-base font-semibold tracking-tight">
              Transaction history
            </h2>
            <p className="text-foreground/55 text-xs">
              All credit grants, top-ups, and consumption events.
            </p>
          </div>
          {transactions && transactions.total > (transactions.items.length ?? 0) && (
            <span className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
              Showing {transactions.items.length} / {transactions.total}
            </span>
          )}
        </div>

        {txLoading ? (
          <div className="p-6">
            <LoadingState variant="skeleton-list" rows={4} />
          </div>
        ) : !transactions || transactions.items.length === 0 ? (
          <div className="border-foreground/10 m-6 rounded-xl border-2 border-dashed p-10 text-center">
            <Coins className="text-foreground/40 mx-auto h-8 w-8" />
            <p className="text-foreground/65 mt-3 text-sm">No transactions yet</p>
            <p className="text-foreground/45 mt-1 text-xs">
              Activity will show here once you start using AI features.
            </p>
          </div>
        ) : (
          <ul className="divide-foreground/10 divide-y">
            {transactions.items.map((tx) => (
              <li
                key={tx.id}
                className="flex flex-wrap items-center justify-between gap-3 px-6 py-4"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-foreground text-sm font-medium">
                    {tx.description ?? "Credit transaction"}
                  </p>
                  <p className="text-foreground/55 mt-1 flex flex-wrap items-center gap-2 font-mono text-[11px] tracking-wider uppercase">
                    <span
                      className={cn(
                        "inline-flex rounded-full border px-2 py-0.5",
                        tx.delta > 0
                          ? "border-brand/30 text-brand"
                          : "border-foreground/15 text-foreground/55",
                      )}
                    >
                      {humanizeType(tx.type)}
                    </span>
                    <span>{formatDateTime(tx.created_at)}</span>
                  </p>
                </div>
                <div className="text-right">
                  <p
                    className={cn(
                      "font-mono text-sm font-semibold tabular-nums",
                      tx.delta > 0 ? "text-brand" : "text-foreground",
                    )}
                  >
                    {tx.delta > 0 ? "+" : ""}
                    {tx.delta.toLocaleString()}
                  </p>
                  <p className="text-foreground/45 mt-0.5 font-mono text-[10px] tracking-wider uppercase">
                    bal {tx.balance_after.toLocaleString()}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="text-foreground/55 inline-flex items-center gap-1.5 text-xs">
        Need a custom credit pack?{" "}
        <Link
          href="/contact"
          className="text-foreground hover:text-foreground/80 inline-flex items-center gap-1 font-medium underline-offset-4 hover:underline"
        >
          Contact us
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </p>
    </div>
  );
}
