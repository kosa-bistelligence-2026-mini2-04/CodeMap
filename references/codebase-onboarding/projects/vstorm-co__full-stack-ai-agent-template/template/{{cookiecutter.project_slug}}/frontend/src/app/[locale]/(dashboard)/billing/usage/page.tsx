{% raw %}"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Download } from "lucide-react";

import { PageHero } from "@/components/dashboard/page-hero";
import { LoadingState } from "@/components/states";
import { apiClient } from "@/lib/api-client";

interface UsageAggregate {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_tokens: number;
  total_credits_charged: number;
  total_calls: number;
  by_model: Array<{
    model: string;
    provider: string;
    input_tokens: number;
    output_tokens: number;
    credits_charged: number;
    total_calls: number;
  }>;
}

interface UsageDailyBucket {
  day: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  credits_charged: number;
  total_calls: number;
}

interface UsageTimeline {
  buckets: UsageDailyBucket[];
  days: number;
}

interface CreditTransaction {
  id: string;
  delta: number;
  balance_after: number;
  type: string;
  description: string | null;
  created_at: string;
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-border bg-card rounded-2xl border p-5">
      <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">{label}</p>
      <p className="font-display text-foreground mt-2 text-3xl font-bold tabular-nums">{value}</p>
    </div>
  );
}

function ChartCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-border bg-card rounded-2xl border p-5">
      <header className="mb-4">
        <h2 className="text-foreground text-sm font-semibold">{title}</h2>
        {description && <p className="text-foreground/55 mt-0.5 text-xs">{description}</p>}
      </header>
      {children}
    </section>
  );
}

export default function UsageDashboardPage() {
  const [aggregate, setAggregate] = useState<UsageAggregate | null>(null);
  const [timeline, setTimeline] = useState<UsageTimeline | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [agg, tl] = await Promise.all([
        apiClient.get<UsageAggregate>("/billing/me/credits/usage"),
        apiClient.get<UsageTimeline>("/billing/me/credits/usage/timeline?days=30"),
      ]);
      setAggregate(agg);
      setTimeline(tl);
    } catch {
      setAggregate(null);
      setTimeline(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = async () => {
    try {
      const txData = await apiClient.get<{ items: CreditTransaction[] }>(
        "/billing/me/credits/transactions?skip=0&limit=1000",
      );
      const csv = [
        "Date,Type,Delta,Balance After,Description",
        ...txData.items.map((t) =>
          [
            new Date(t.created_at).toISOString(),
            t.type,
            t.delta,
            t.balance_after,
            `"${(t.description ?? "").replace(/"/g, '""')}"`,
          ].join(","),
        ),
      ].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "credits-export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  const byModelChartData =
    aggregate?.by_model.map((m) => ({
      name: m.model.split("-").slice(-2).join("-"),
      input: m.input_tokens,
      output: m.output_tokens,
      credits: m.credits_charged,
    })) ?? [];

  const timelineChartData =
    timeline?.buckets.map((b) => ({
      day: b.day.slice(5), // "MM-DD"
      credits: b.credits_charged,
      calls: b.total_calls,
    })) ?? [];

  const totalTokens = aggregate
    ? aggregate.total_input_tokens + aggregate.total_output_tokens
    : null;

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8 pb-12">
      <PageHero
        eyebrow="Billing · Usage"
        title={
          <>
            Token <em>consumption.</em>
          </>
        }
        description="Credits and tokens used across this organization in the last 30 days, broken down by model and day."
        actions={
          <button
            type="button"
            onClick={handleExport}
            className="border-foreground/15 hover:border-foreground/40 text-foreground inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        }
      />

      {isLoading ? (
        <LoadingState variant="stats" rows={3} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatTile
            label="Credits used"
            value={aggregate?.total_credits_charged.toLocaleString() ?? "—"}
          />
          <StatTile label="Tokens" value={totalTokens?.toLocaleString() ?? "—"} />
          <StatTile label="API calls" value={aggregate?.total_calls.toLocaleString() ?? "—"} />
        </div>
      )}

      {!isLoading && timelineChartData.length > 0 && (
        <ChartCard title="Daily credits" description="Last 30 days of credit consumption.">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={timelineChartData} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 11 }}
                className="fill-muted-foreground"
                interval="preserveStartEnd"
              />
              <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "10px",
                }}
              />
              <Line
                type="monotone"
                dataKey="credits"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      )}

      {!isLoading && byModelChartData.length > 0 && (
        <ChartCard title="Credits by model" description="Where the spend is concentrated.">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={byModelChartData} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} className="fill-muted-foreground" />
              <YAxis tick={{ fontSize: 12 }} className="fill-muted-foreground" />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "10px",
                }}
              />
              <Bar dataKey="credits" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      )}

      {!isLoading && aggregate && aggregate.by_model.length > 0 && (
        <ChartCard title="Per-model breakdown">
          <div className="divide-foreground/10 -mx-1 divide-y">
            {aggregate.by_model.map((m) => (
              <div key={m.model} className="grid grid-cols-4 gap-4 px-1 py-3 text-sm tabular-nums">
                <div className="col-span-2 min-w-0">
                  <p className="text-foreground truncate font-medium">{m.model}</p>
                  <p className="text-foreground/55 text-xs">{m.provider}</p>
                </div>
                <div>
                  <p className="text-foreground/55 text-xs">Tokens</p>
                  <p className="text-foreground font-mono">
                    {(m.input_tokens + m.output_tokens).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-foreground/55 text-xs">Credits</p>
                  <p className="text-foreground font-mono">{m.credits_charged.toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      )}
    </div>
  );
}
{% endraw %}
