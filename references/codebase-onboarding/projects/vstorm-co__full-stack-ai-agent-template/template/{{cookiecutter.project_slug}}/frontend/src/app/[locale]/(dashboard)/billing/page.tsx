"use client";

import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  CreditCard,
  Download,
  ExternalLink,
  HardDrive,
  Receipt,
  Sparkles,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { UsageGauge } from "@/components/billing/usage-gauge";
import { PageHero } from "@/components/dashboard/page-hero";
import { LoadingState } from "@/components/states";
import { Button } from "@/components/ui";
import {
  useBilling,
  useCredits,
  useInvoices,
  useMembers,
  useOrganizations,
  useSubscription,
} from "@/hooks";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<string, string> = {
  trialing: "Trial",
  active: "Active",
  past_due: "Past due",
  canceled: "Canceled",
  unpaid: "Unpaid",
  incomplete: "Incomplete",
  incomplete_expired: "Expired",
  paused: "Paused",
};

const STATUS_TONES: Record<string, string> = {
  trialing: "border-foreground/15 text-foreground/70",
  active: "bg-brand text-brand-foreground border-transparent",
  past_due: "bg-yellow-500/10 text-yellow-500 border-yellow-500/30",
  canceled: "bg-destructive/10 text-destructive border-destructive/30",
  unpaid: "bg-destructive/10 text-destructive border-destructive/30",
  incomplete: "border-foreground/15 text-foreground/70",
  incomplete_expired: "border-foreground/15 text-foreground/55",
  paused: "border-foreground/15 text-foreground/70",
};

function formatCurrency(amountCents: number, currency = "USD"): string {
  return (amountCents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
    minimumFractionDigits: 0,
  });
}

function formatBytes(bytes: number): string {
  if (!bytes || bytes < 0) return "0 B";
  const KB = 1024;
  const MB = KB * 1024;
  const GB = MB * 1024;
  if (bytes >= GB) return `${(bytes / GB).toFixed(2)} GB`;
  if (bytes >= MB) return `${(bytes / MB).toFixed(1)} MB`;
  if (bytes >= KB) return `${Math.round(bytes / KB)} KB`;
  return `${bytes} B`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function BillingHubPage() {
  const searchParams = useSearchParams();
  const { activeOrg, fetchOrgs } = useOrganizations();
  const { members } = useMembers(activeOrg?.id ?? "");
  const { subscription, isLoading: subLoading } = useSubscription();
  const { balance } = useCredits();
  const { invoices, isLoading: invoicesLoading } = useInvoices();
  const { openPortal, isLoading: portalLoading } = useBilling();
  const [storage, setStorage] = useState<{ total_bytes: number; limit_bytes: number } | null>(null);

  useEffect(() => {
    fetchOrgs();
  }, [fetchOrgs]);

  useEffect(() => {
    apiClient
      .get<{ total_bytes: number; limit_bytes: number }>("/billing/me/storage")
      .then(setStorage)
      .catch(() => setStorage(null));
  }, []);

  useEffect(() => {
    if (searchParams.get("success") === "1") {
      toast.success("Subscription updated successfully");
    }
  }, [searchParams]);

  const status = subscription?.status ?? "free";
  const statusLabel = STATUS_LABELS[status] ?? "Free";
  const statusTone = STATUS_TONES[status] ?? "border-foreground/15 text-foreground/70";
  const planName = subscription?.price?.plan?.display_name ?? "Free";
  const seatsUsed = members?.length ?? 0;
  const seatsLimit = subscription?.seats_quantity ?? activeOrg?.seats_limit ?? null;

  // Approximate "monthly credits limit" — falls back to balance + headroom when
  // we don't know the plan grant. Credits page has the precise view.
  const creditsLimit =
    subscription?.price?.plan?.monthly_credits_base ??
    (balance ? Math.max(1000, balance.balance + 1000) : undefined);

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 pb-10">
      <PageHero
        eyebrow="Billing"
        title={
          <>
            {activeOrg?.name ?? "Your workspace"}
            <em className="text-foreground/30">.</em>
          </>
        }
        description="Plan, usage, invoices, payment methods — all in one place."
        actions={
          <Button
            onClick={() => openPortal()}
            disabled={portalLoading}
            variant="outline"
            className="rounded-full"
          >
            {portalLoading ? (
              "Opening…"
            ) : (
              <>
                <ExternalLink className="mr-2 h-4 w-4" />
                Manage in Stripe
              </>
            )}
          </Button>
        }
      />

      {/* Current plan card */}
      <section className="border-foreground/10 bg-card relative overflow-hidden rounded-3xl border p-6 sm:p-8">
        <div className="bg-brand/[0.06] pointer-events-none absolute -top-32 -right-32 h-72 w-72 rounded-full blur-[120px]" />
        <div className="relative grid gap-6 md:grid-cols-[1.4fr_1fr] md:items-center">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
                Current plan
              </span>
              <span
                className={cn(
                  "inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider uppercase",
                  statusTone,
                )}
              >
                {statusLabel}
              </span>
            </div>
            <p className="font-display text-foreground mt-3 text-3xl font-bold tracking-tight">
              {planName}
            </p>
            {subscription ? (
              <p className="text-foreground/65 mt-2 text-sm">
                Renews{" "}
                <span className="text-foreground font-medium">
                  {formatDate(subscription.current_period_end)}
                </span>
                {subscription.cancel_at_period_end && (
                  <span className="text-destructive ml-2 font-mono text-[11px] tracking-wider uppercase">
                    · Cancels at period end
                  </span>
                )}
              </p>
            ) : !subLoading ? (
              <p className="text-foreground/65 mt-2 text-sm">
                Free plan. Upgrade to unlock more credits, seats, and integrations.
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2 md:justify-end">
            {!subscription && (
              <Button asChild className="rounded-full">
                <Link href={ROUTES.PRICING}>
                  See plans
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            )}
            {subscription && (
              <Button asChild variant="outline" className="rounded-full">
                <Link href={ROUTES.PRICING}>Compare plans</Link>
              </Button>
            )}
          </div>
        </div>
      </section>

      {/* Usage gauges */}
      <section>
        <h2 className="font-display text-foreground mb-4 text-base font-semibold tracking-tight">
          This period
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <UsageGauge
            label="Credits"
            icon={Sparkles}
            used={balance?.balance ?? 0}
            limit={creditsLimit}
            unit="credits"
            hint={
              balance && balance.low_threshold > 0
                ? `Auto-refill threshold ${balance.low_threshold.toLocaleString()}`
                : undefined
            }
          />
          {seatsLimit !== null && (
            <UsageGauge
              label="Seats"
              icon={Users}
              used={seatsUsed}
              limit={seatsLimit}
              unit="seats"
              hint="Add seats from the Stripe portal"
            />
          )}
          <UsageGauge
            label="Storage"
            icon={HardDrive}
            used={storage?.total_bytes ?? 0}
            limit={storage?.limit_bytes ?? 0}
            format={formatBytes}
            hint={
              storage ? `Chat attachments + indexed RAG documents` : "Failed to load storage usage"
            }
          />
        </div>
      </section>

      {/* Quick links to subroutes */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <SubLink
          href="/billing/credits"
          icon={Sparkles}
          title="Credits"
          description="Balance, transactions, top-up"
        />
        <SubLink
          href="/billing/usage"
          icon={Activity}
          title="Usage"
          description="Per-model breakdown, by-day timeline"
        />
        <SubLink
          href="/billing/invoices"
          icon={Receipt}
          title="Invoices"
          description="Download PDFs, view history"
        />
        <SubLink
          href="/billing/payment-methods"
          icon={CreditCard}
          title="Payment methods"
          description="Cards on file, set default"
        />
        <SubLink
          href="/billing/subscription"
          icon={ArrowUpRight}
          title="Subscription"
          description="Change plan, manage seats"
        />
      </section>

      {/* Recent invoices */}
      <section className="border-foreground/10 bg-card rounded-2xl border p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="font-display text-foreground text-base font-semibold tracking-tight">
              Recent invoices
            </h2>
            <p className="text-foreground/55 text-xs">
              Last {Math.min(5, invoices.length)} of {invoices.length}
            </p>
          </div>
          <Button asChild variant="ghost" size="sm" className="rounded-full">
            <Link href="/billing/invoices">View all →</Link>
          </Button>
        </div>

        {invoicesLoading ? (
          <LoadingState variant="skeleton-list" rows={3} />
        ) : invoices.length === 0 ? (
          <div className="text-foreground/55 border-foreground/10 bg-background rounded-xl border-2 border-dashed p-8 text-center text-sm">
            No invoices yet. They appear here after your first paid period.
          </div>
        ) : (
          <ul className="border-foreground/10 divide-foreground/10 -mx-2 divide-y overflow-hidden rounded-xl">
            {invoices.slice(0, 5).map((inv) => (
              <li
                key={inv.id}
                className="hover:bg-foreground/[0.03] flex items-center justify-between gap-3 px-4 py-3 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-foreground text-sm font-medium">
                    {inv.number ?? `Invoice ${inv.id.slice(0, 8)}`}
                  </p>
                  <p className="text-foreground/55 mt-0.5 font-mono text-[11px] tracking-wider uppercase">
                    {formatDate(inv.period_start)} — {formatDate(inv.period_end)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-foreground text-sm font-semibold">
                    {formatCurrency(inv.amount_due, inv.currency)}
                  </p>
                  <p
                    className={cn(
                      "mt-0.5 font-mono text-[10px] tracking-wider uppercase",
                      inv.status === "paid"
                        ? "text-brand"
                        : inv.status === "open"
                          ? "text-yellow-500"
                          : "text-foreground/55",
                    )}
                  >
                    {inv.status}
                  </p>
                </div>
                {inv.invoice_pdf && (
                  <Button asChild variant="ghost" size="sm" className="shrink-0 rounded-full">
                    <a
                      href={inv.invoice_pdf}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Download PDF"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </a>
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function SubLink({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string;
  icon: typeof Activity;
  title: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="lift border-foreground/10 hover:border-brand/40 bg-card group flex items-center gap-3 rounded-2xl border p-4 transition-all"
    >
      <span className="bg-brand/15 text-foreground group-hover:bg-brand group-hover:text-brand-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-colors">
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-foreground text-sm font-semibold">{title}</p>
        <p className="text-foreground/55 truncate text-xs">{description}</p>
      </div>
      <ArrowUpRight className="text-foreground/30 group-hover:text-foreground h-4 w-4 transition-all group-hover:rotate-45" />
    </Link>
  );
}
