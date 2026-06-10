"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  CreditCard,
  Database,
  List,
  MessageSquare,
  Minus,
  Search,
  Sparkles,
  Star,
} from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

import { OnboardingBanner } from "@/components/dashboard/onboarding-banner";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { SegmentedControl } from "@/components/dashboard/segmented-control";
import { StatCard } from "@/components/dashboard/stat-card";
import { SubscriptionChip } from "@/components/dashboard/subscription-chip";
import { TeamSummary } from "@/components/dashboard/team-summary";
import { ToolUsage } from "@/components/dashboard/tool-usage";
import { TopModels } from "@/components/dashboard/top-models";
import { UsageTimeline } from "@/components/dashboard/usage-timeline";
import { useAuth } from "@/hooks";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { listCollections, getCollectionInfo } from "@/lib/rag-api";
import type { HealthResponse } from "@/types";

interface CreditBalance {
  balance: number;
  low_threshold: number;
}

interface UsageBucket {
  day: string;
  credits_charged: number;
  total_calls: number;
}

interface UsageTimelineRead {
  buckets: UsageBucket[];
  days: number;
}

interface ConversationsResponse {
  total?: number;
  items: Array<{ id: string }>;
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function pctDelta(current: number[], prior: number[]): number | undefined {
  const cur = current.reduce((a, b) => a + b, 0);
  const prev = prior.reduce((a, b) => a + b, 0);
  if (prev === 0) return cur > 0 ? 100 : 0;
  return ((cur - prev) / prev) * 100;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [credits, setCredits] = useState<CreditBalance | null>(null);
  const [creditsLoading, setCreditsLoading] = useState(true);
  const [conversations, setConversations] = useState<{ total: number } | null>(null);
  const [convLoading, setConvLoading] = useState(true);
  const [ragStats, setRagStats] = useState<{ collections: number; vectors: number } | null>(null);
  const [timeline, setTimeline] = useState<UsageBucket[] | null>(null);
  const [period, setPeriod] = useState<7 | 30 | 90>(7);

  useEffect(() => {
    apiClient
      .get<HealthResponse>("/health")
      .then((d) => {
        setHealth(d);
        setHealthError(false);
      })
      .catch(() => setHealthError(true));
    apiClient
      .get<CreditBalance>("/billing/me/credits")
      .then(setCredits)
      .catch(() => setCredits(null))
      .finally(() => setCreditsLoading(false));

    apiClient
      .get<ConversationsResponse>("/conversations?limit=1")
      .then((d) => setConversations({ total: d.total ?? d.items?.length ?? 0 }))
      .catch(() => setConversations({ total: 0 }))
      .finally(() => setConvLoading(false));
    listCollections()
      .then(async (list) => {
        let totalVectors = 0;
        for (const name of list.items) {
          try {
            const info = await getCollectionInfo(name);
            totalVectors += info.total_vectors;
          } catch {
            /* ignore */
          }
        }
        setRagStats({ collections: list.items.length, vectors: totalVectors });
      })
      .catch(() => setRagStats({ collections: 0, vectors: 0 }));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setTimeline(null);
    apiClient
      .get<UsageTimelineRead>(`/billing/me/credits/usage/timeline?days=${period * 2}`)
      .then((d) => {
        if (!cancelled) setTimeline(d.buckets);
      })
      .catch(() => {
        if (!cancelled) setTimeline([]);
      });
    return () => {
      cancelled = true;
    };
  }, [period]);

  const creditsSpark = (timeline ?? []).slice(-period).map((b) => b.credits_charged);
  const callsSpark = (timeline ?? []).slice(-period).map((b) => b.total_calls);
  const creditsDelta = timeline
    ? pctDelta(
        timeline.slice(-period).map((b) => b.credits_charged),
        timeline.slice(-period * 2, -period).map((b) => b.credits_charged),
      )
    : undefined;
  const callsDelta = timeline
    ? pctDelta(
        timeline.slice(-period).map((b) => b.total_calls),
        timeline.slice(-period * 2, -period).map((b) => b.total_calls),
      )
    : undefined;
  const deltaLabel = `vs prior ${period}d`;

  const firstName = user?.full_name?.split(" ")[0] || user?.email?.split("@")[0];

  return (
    <div className="space-y-6 pb-8">
      <OnboardingBanner />

      {/* HERO BLOCK — greeting + status pulse */}
      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        {/* Greeting card */}
        <div className="border-foreground/10 bg-foreground/[0.02] relative isolate overflow-hidden rounded-3xl border p-7 sm:p-9">
          <div
            aria-hidden
            className="pointer-events-none absolute -top-24 -right-24 -z-10 h-[340px] w-[340px] rounded-full blur-3xl"
            style={{
              background:
                "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.28), transparent 65%)",
            }}
          />
          <div
            aria-hidden
            className="bg-dots pointer-events-none absolute inset-0 -z-10 opacity-50"
          />

          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Dashboard
          </p>
          <h1 className="font-display text-foreground mt-2 text-3xl leading-[1.05] font-bold tracking-tight sm:text-4xl [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
            {getGreeting()}
            {firstName ? (
              <>
                ,<br />
                <em>{firstName}.</em>
              </>
            ) : (
              <span className="text-foreground/30">.</span>
            )}
          </h1>
          <p className="text-foreground/65 mt-4 max-w-md text-sm">
            Here&apos;s what&apos;s happening with your workspace.
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link
              href={ROUTES.CHAT}
              className="bg-foreground text-background hover:bg-foreground/90 group inline-flex items-center gap-3 rounded-full py-2 pr-2 pl-5 text-sm font-medium transition-colors"
            >
              <span>New chat</span>
              <span className="bg-brand text-brand-foreground flex h-8 w-8 items-center justify-center rounded-full transition-transform group-hover:rotate-45">
                <ArrowUpRight className="h-3.5 w-3.5" />
              </span>
            </Link>
            <SearchHint />
          </div>
        </div>

        {/* Status pulse card */}
        <div className="border-foreground/10 bg-foreground/[0.02] relative flex flex-col justify-between gap-6 overflow-hidden rounded-3xl border p-6 sm:p-7">
          <div>
            <p className="text-foreground/55 mb-4 font-mono text-[11px] tracking-wider uppercase">
              Status
            </p>
            <div className="flex items-center gap-3">
              <span
                aria-hidden
                className={cn(
                  "inline-block h-2 w-2 rounded-full",
                  healthError ? "bg-destructive" : "bg-brand animate-pulse",
                )}
                style={
                  healthError
                    ? undefined
                    : { boxShadow: "0 0 14px var(--color-brand), 0 0 4px var(--color-brand)" }
                }
              />
              <span className="font-display text-foreground text-lg font-semibold">
                {healthError ? "API offline" : health?.status || "Operational"}
              </span>
            </div>
            {health?.version && (
              <p className="text-foreground/45 mt-1 ml-5 font-mono text-[10px] tracking-wider uppercase">
                v{health.version}
              </p>
            )}
          </div>

          <dl className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between">
              <dt className="text-foreground/55 font-mono tracking-wider uppercase">Collections</dt>
              <dd className="text-foreground font-mono tabular-nums">
                {ragStats ? ragStats.collections : "—"}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-foreground/55 font-mono tracking-wider uppercase">Vectors</dt>
              <dd className="text-foreground font-mono tabular-nums">
                {ragStats ? ragStats.vectors.toLocaleString() : "—"}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-foreground/55 font-mono tracking-wider uppercase">Plan</dt>
              <dd>
                <SubscriptionChip />
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* WORKSPACE METRICS */}
      <div className="flex items-center justify-between">
        <h2 className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          Workspace metrics
        </h2>
        <SegmentedControl
          value={String(period)}
          onChange={(v) => setPeriod(Number(v) as 7 | 30 | 90)}
          options={[
            { label: "7d", value: "7" },
            { label: "30d", value: "30" },
            { label: "90d", value: "90" },
          ]}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {/* Featured Credits card — spans 2 cols */}
        <FeaturedCreditsCard
          balance={credits?.balance}
          loading={creditsLoading}
          spark={creditsSpark}
          delta={creditsDelta}
          deltaLabel={deltaLabel}
          lowThreshold={credits?.low_threshold ?? 0}
        />
        <StatCard
          label="Conversations"
          value={convLoading ? "—" : (conversations?.total ?? 0).toLocaleString()}
          icon={MessageSquare}
          loading={convLoading}
        />
        <StatCard
          label={`API calls (${period}d)`}
          value={timeline ? callsSpark.reduce((a, b) => a + b, 0).toLocaleString() : "—"}
          icon={Activity}
          delta={callsDelta}
          deltaLabel={deltaLabel}
          spark={callsSpark.length >= 2 ? callsSpark : [0, 0]}
          loading={!timeline}
        />
        <StatCard
          label="Knowledge base"
          value={ragStats ? ragStats.vectors.toLocaleString() : "—"}
          unit={ragStats ? `vector${ragStats.vectors === 1 ? "" : "s"}` : undefined}
          icon={Database}
          loading={!ragStats}
        />
      </div>

      {/* Manage billing link */}
      <div className="flex justify-end">
        <Link
          href={ROUTES.BILLING}
          className="text-foreground/55 hover:text-foreground inline-flex items-center gap-1.5 font-mono text-[10px] tracking-wider uppercase transition-colors"
        >
          <CreditCard className="h-3.5 w-3.5" />
          Manage billing →
        </Link>
      </div>

      {/* Usage timeline (full width) */}
      <UsageTimeline />

      {/* Activity + behavior insights */}
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <RecentActivity />
        <TopModels />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ToolUsage />
        <TeamSummary />
      </div>

      <QuickActions />

      {/* Admin row */}
      {user?.role === "admin" && (
        <div>
          <h2 className="font-display text-foreground mb-3 text-base font-semibold">
            Admin actions
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <AdminTile
              icon={Star}
              label="Response ratings"
              description="View and manage ratings"
              href={ROUTES.ADMIN_RATINGS}
            />
            <AdminTile
              icon={List}
              label="All conversations"
              description="Inspect any user's chats"
              href={ROUTES.ADMIN_CONVERSATIONS}
            />
          </div>
        </div>
      )}
    </div>
  );
}

interface FeaturedCreditsCardProps {
  balance: number | undefined;
  loading: boolean;
  spark: number[];
  delta: number | undefined;
  deltaLabel: string;
  lowThreshold: number;
}

function FeaturedCreditsCard({
  balance,
  loading,
  spark,
  delta,
  deltaLabel,
  lowThreshold,
}: FeaturedCreditsCardProps) {
  const belowThreshold = balance !== undefined && lowThreshold > 0 && balance < lowThreshold;
  const trend = typeof delta === "number" ? (delta > 0 ? "up" : delta < 0 ? "down" : "flat") : null;

  if (loading) {
    return (
      <div className="border-foreground/10 bg-foreground/[0.02] relative animate-pulse space-y-3 overflow-hidden rounded-2xl border p-6 sm:col-span-2 lg:col-span-2">
        <div className="bg-foreground/10 h-3 w-1/3 rounded-full" />
        <div className="bg-foreground/15 h-12 w-1/2 rounded-md" />
        <div className="bg-foreground/8 h-14 w-full rounded-md" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "relative isolate overflow-hidden rounded-2xl border p-6 sm:col-span-2 lg:col-span-2",
        belowThreshold
          ? "border-destructive/40 bg-destructive/[0.04]"
          : "border-brand/40 bg-foreground/[0.02]",
      )}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-28 -left-16 -z-10 h-[340px] w-[340px] rounded-full blur-3xl"
        style={{
          background: belowThreshold
            ? "radial-gradient(circle, oklch(from var(--color-destructive) l c h / 0.25), transparent 65%)"
            : "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.35), transparent 65%)",
        }}
      />

      <div className="flex items-start justify-between gap-2">
        <p className="text-foreground/55 inline-flex items-center gap-1.5 font-mono text-[11px] tracking-wider uppercase">
          <Sparkles className="text-brand h-3 w-3" />
          Credits balance
        </p>
        {trend && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 font-mono text-[11px] font-semibold tabular-nums",
              trend === "up" && "bg-chart/15 text-chart",
              trend === "down" && "bg-destructive/10 text-destructive",
              trend === "flat" && "bg-foreground/8 text-foreground/65",
            )}
          >
            {trend === "up" && <ArrowUpRight className="h-3 w-3" />}
            {trend === "down" && <ArrowDownRight className="h-3 w-3" />}
            {trend === "flat" && <Minus className="h-3 w-3" />}
            {Math.abs(delta!).toFixed(1)}%
          </span>
        )}
      </div>

      <div className="mt-4 flex items-baseline gap-3">
        <span className="text-foreground font-mono text-[clamp(2.5rem,7vw,4.75rem)] leading-[0.9] font-medium tracking-tighter tabular-nums">
          {balance !== undefined ? balance.toLocaleString() : "—"}
        </span>
      </div>

      <p className="text-foreground/45 mt-2 font-mono text-[10px] tracking-wider uppercase">
        {trend ? deltaLabel : belowThreshold ? "Below auto-refill threshold" : "Live balance"}
      </p>

      {spark.length >= 2 && (
        <div className="-mx-2 mt-4 h-14">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={spark.map((v, i) => ({ i, v }))}>
              <defs>
                <linearGradient id="featured-spark" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-brand)" stopOpacity={0.55} />
                  <stop offset="100%" stopColor="var(--color-brand)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke="var(--color-brand)"
                strokeWidth={2}
                fill="url(#featured-spark)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function SearchHint() {
  return (
    <div className="border-foreground/15 bg-background hidden items-center gap-2 rounded-full border px-3 py-1.5 text-xs sm:inline-flex">
      <Search className="text-foreground/45 h-3.5 w-3.5" />
      <span className="text-foreground/55">Search</span>
      <kbd className="border-foreground/15 bg-card text-foreground/65 rounded-md border px-1.5 py-0.5 font-mono text-[10px]">
        ⌘K
      </kbd>
    </div>
  );
}

function AdminTile({
  icon: Icon,
  label,
  description,
  href,
}: {
  icon: typeof Star;
  label: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="lift border-border hover:border-foreground/30 bg-card flex items-center gap-3 rounded-2xl border p-4 transition-colors"
    >
      <span className="bg-foreground/8 text-foreground flex h-9 w-9 items-center justify-center rounded-full">
        <Icon className="h-4 w-4" />
      </span>
      <div className="flex-1">
        <p className="text-foreground text-sm font-semibold">{label}</p>
        <p className="text-foreground/55 text-xs">{description}</p>
      </div>
    </Link>
  );
}
