"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronRight as ChevronRightIcon,
  Filter,
  RefreshCw,
  Search,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface StripeEvent {
  id: string;
  type: string;
  status: "processed" | "failed" | "pending";
  livemode: boolean;
  customer_email?: string | null;
  amount_cents?: number | null;
  currency?: string | null;
  created_at: string;
  attempts: number;
  last_error?: string | null;
}

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;
type SortDir = "asc" | "desc";
type SortKey = "type" | "customer_email" | "amount_cents" | "status" | "created_at";
type StatusFilter = "all" | "processed" | "failed" | "pending";

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

function formatAmount(
  cents: number | null | undefined,
  currency: string | null | undefined,
): string {
  if (typeof cents !== "number") return "—";
  return (cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: (currency ?? "USD").toUpperCase(),
    minimumFractionDigits: 0,
  });
}

const STUB_EVENTS: StripeEvent[] = [
  {
    id: "evt_3PqWzL2eZvKYlo2C0K",
    type: "invoice.payment_succeeded",
    status: "processed",
    livemode: true,
    customer_email: "maya@lumenlabs.co",
    amount_cents: 2900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzM2eZvKYlo2DRT",
    type: "customer.subscription.updated",
    status: "processed",
    livemode: true,
    customer_email: "jonas@stash.ai",
    created_at: new Date(Date.now() - 1000 * 60 * 47).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzN2eZvKYlo2EX7",
    type: "invoice.payment_failed",
    status: "failed",
    livemode: true,
    customer_email: "ops@northwind.io",
    amount_cents: 9900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    attempts: 3,
    last_error: "Card declined: insufficient_funds",
  },
  {
    id: "evt_3PqWzO2eZvKYlo2F8M",
    type: "checkout.session.completed",
    status: "processed",
    livemode: true,
    customer_email: "priya@example.io",
    amount_cents: 2900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzP2eZvKYlo2GZQ",
    type: "customer.subscription.deleted",
    status: "processed",
    livemode: false,
    customer_email: "test@example.com",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(),
    attempts: 1,
  },
  {
    id: "evt_3PqWzQ2eZvKYlo2HHb",
    type: "invoice.created",
    status: "pending",
    livemode: true,
    customer_email: "billing@megacorp.com",
    amount_cents: 49900,
    currency: "usd",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
    attempts: 0,
  },
];

export default function StripeEventsPage() {
  const [events, setEvents] = useState<StripeEvent[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [pageSize, setPageSize] = useState(50);
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<{ by: SortKey; dir: SortDir }>({
    by: "created_at",
    dir: "desc",
  });
  const [expanded, setExpanded] = useState<string | null>(null);
  const [usingStub, setUsingStub] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiClient
        .get<{ items: StripeEvent[] }>("/admin/stripe-events?limit=500")
        .catch(() => null);
      if (data) {
        setEvents(data.items);
        setUsingStub(false);
      } else {
        setEvents(STUB_EVENTS);
        setUsingStub(true);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Reset page on filter change
  useEffect(() => {
    setPage(0);
  }, [search, statusFilter, pageSize, sort.by, sort.dir]);

  const filteredSorted = useMemo(() => {
    if (!events) return [];
    const q = search.trim().toLowerCase();
    const filtered = events.filter((e) => {
      if (statusFilter !== "all" && e.status !== statusFilter) return false;
      if (q) {
        return (
          e.id.toLowerCase().includes(q) ||
          e.type.toLowerCase().includes(q) ||
          (e.customer_email ?? "").toLowerCase().includes(q)
        );
      }
      return true;
    });
    filtered.sort((a, b) => {
      const av = (a[sort.by] ?? "") as string | number;
      const bv = (b[sort.by] ?? "") as string | number;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sort.dir === "asc" ? cmp : -cmp;
    });
    return filtered;
  }, [events, search, statusFilter, sort.by, sort.dir]);

  const total = filteredSorted.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const pageItems = useMemo(
    () => filteredSorted.slice(page * pageSize, (page + 1) * pageSize),
    [filteredSorted, page, pageSize],
  );

  const handleReplay = async (evt: StripeEvent) => {
    if (usingStub) {
      toast.info("Demo mode — backend wiring required (POST /admin/stripe-events/{id}/replay)");
      return;
    }
    try {
      await apiClient.post(`/admin/stripe-events/${evt.id}/replay`);
      toast.success(`Replayed ${evt.type}`);
      load();
    } catch {
      toast.error("Replay failed");
    }
  };

  const toggleSort = (key: SortKey) =>
    setSort((s) =>
      s.by === key ? { by: key, dir: s.dir === "asc" ? "desc" : "asc" } : { by: key, dir: "desc" },
    );

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex items-start justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Stripe events
          </p>
          <h2 className="font-display text-foreground mt-1 text-xl font-semibold tracking-tight [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
            Webhook <em>event log.</em>
          </h2>
          <p className="text-foreground/65 mt-1 text-sm">
            Replay failed events to debug billing flows.
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={load} className="rounded-full">
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {usingStub && (
        <div className="border-foreground/10 bg-muted/40 mb-4 flex items-start gap-3 rounded-lg border p-3">
          <Filter className="text-muted-foreground mt-0.5 h-4 w-4 shrink-0" />
          <div className="min-w-0 flex-1 text-xs">
            <p className="text-foreground font-medium">Demo data</p>
            <p className="text-muted-foreground mt-0.5">
              Backend wiring required. Expected: <code>GET /admin/stripe-events</code>,{" "}
              <code>POST /admin/stripe-events/&#123;id&#125;/replay</code>.
            </p>
          </div>
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[240px] flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder="Search id, type, customer…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="processed">Processed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
          </SelectContent>
        </Select>

        <Select value={String(pageSize)} onValueChange={(v) => setPageSize(Number(v))}>
          <SelectTrigger className="w-[110px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZE_OPTIONS.map((n) => (
              <SelectItem key={n} value={String(n)}>
                {n} / page
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="text-muted-foreground mb-2 text-xs">{total} total</div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8" />
            <SortableHead
              active={sort.by === "type"}
              dir={sort.dir}
              onClick={() => toggleSort("type")}
            >
              Event
            </SortableHead>
            <SortableHead
              active={sort.by === "customer_email"}
              dir={sort.dir}
              onClick={() => toggleSort("customer_email")}
            >
              Customer
            </SortableHead>
            <SortableHead
              active={sort.by === "amount_cents"}
              dir={sort.dir}
              onClick={() => toggleSort("amount_cents")}
            >
              Amount
            </SortableHead>
            <SortableHead
              active={sort.by === "status"}
              dir={sort.dir}
              onClick={() => toggleSort("status")}
            >
              Status
            </SortableHead>
            <SortableHead
              active={sort.by === "created_at"}
              dir={sort.dir}
              onClick={() => toggleSort("created_at")}
            >
              Time
            </SortableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading && events === null
            ? Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 7 }).map((__, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            : pageItems.map((e) => {
                const isExpanded = expanded === e.id;
                return (
                  <Fragment key={e.id}>
                    <TableRow
                      className="cursor-pointer"
                      onClick={() => setExpanded((cur) => (cur === e.id ? null : e.id))}
                    >
                      <TableCell>
                        {isExpanded ? (
                          <ChevronDown className="text-muted-foreground h-4 w-4" />
                        ) : (
                          <ChevronRightIcon className="text-muted-foreground h-4 w-4" />
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="min-w-0">
                          <p className="text-foreground truncate text-sm font-medium">{e.type}</p>
                          <p className="text-muted-foreground truncate font-mono text-xs">{e.id}</p>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {e.customer_email ?? "—"}
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {formatAmount(e.amount_cents, e.currency)}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={e.status} attempts={e.attempts} />
                      </TableCell>
                      <TableCell className="text-muted-foreground text-xs">
                        {formatDateTime(e.created_at)}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(ev) => {
                            ev.stopPropagation();
                            handleReplay(e);
                          }}
                          aria-label="Replay event"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                        </Button>
                      </TableCell>
                    </TableRow>
                    {isExpanded && (
                      <TableRow className="bg-muted/30">
                        <TableCell colSpan={7}>
                          <dl className="grid gap-3 p-2 text-xs sm:grid-cols-2">
                            <KV label="Event ID" value={e.id} mono />
                            <KV label="Type" value={e.type} mono />
                            <KV label="Mode" value={e.livemode ? "live" : "test"} />
                            <KV label="Attempts" value={String(e.attempts)} />
                            {e.customer_email && <KV label="Customer" value={e.customer_email} />}
                            {typeof e.amount_cents === "number" && (
                              <KV label="Amount" value={formatAmount(e.amount_cents, e.currency)} />
                            )}
                            <KV label="Created" value={new Date(e.created_at).toLocaleString()} />
                            {e.last_error && (
                              <KV label="Last error" value={e.last_error} accent="danger" />
                            )}
                          </dl>
                          <div className="mt-2 flex flex-wrap items-center gap-2 px-2 pb-2">
                            <Button size="sm" variant="outline" onClick={() => handleReplay(e)}>
                              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                              Replay
                            </Button>
                            <a
                              href={`https://dashboard.stripe.com/${e.livemode ? "" : "test/"}events/${e.id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-muted-foreground hover:text-foreground inline-flex items-center text-xs"
                            >
                              Open in Stripe →
                            </a>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                );
              })}
          {!loading && total === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-muted-foreground py-8 text-center">
                No events match.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <PaginationBar
        page={page}
        pageSize={pageSize}
        total={total}
        totalPages={totalPages}
        isLoading={loading}
        onPrev={() => setPage((p) => Math.max(0, p - 1))}
        onNext={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
      />
    </div>
  );
}

function StatusBadge({ status, attempts }: { status: StripeEvent["status"]; attempts: number }) {
  if (status === "processed") {
    return <Badge variant="default">Processed{attempts > 1 ? ` · ${attempts}×` : ""}</Badge>;
  }
  if (status === "failed") {
    return <Badge variant="destructive">Failed{attempts > 1 ? ` · ${attempts}×` : ""}</Badge>;
  }
  return <Badge variant="secondary">Pending</Badge>;
}

function KV({
  label,
  value,
  mono,
  accent,
}: {
  label: string;
  value: string;
  mono?: boolean;
  accent?: "danger";
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-muted-foreground text-[10px] tracking-wider uppercase">{label}</dt>
      <dd
        className={cn(
          "break-all",
          mono ? "font-mono" : "",
          accent === "danger" ? "text-destructive" : "text-foreground",
        )}
      >
        {value}
      </dd>
    </div>
  );
}

function SortableHead({
  active,
  dir,
  onClick,
  children,
}: {
  active: boolean;
  dir: SortDir;
  onClick: () => void;
  children: React.ReactNode;
}) {
  const Icon = !active ? ArrowUpDown : dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <TableHead>
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "hover:text-foreground inline-flex items-center gap-1 text-left transition-colors",
          active && "text-foreground",
        )}
      >
        {children}
        <Icon className={cn("h-3 w-3", !active && "opacity-40")} aria-hidden />
      </button>
    </TableHead>
  );
}

function PaginationBar({
  page,
  pageSize,
  total,
  totalPages,
  isLoading,
  onPrev,
  onNext,
}: {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  isLoading: boolean;
  onPrev: () => void;
  onNext: () => void;
}) {
  if (total === 0) return null;
  const start = page * pageSize + 1;
  const end = Math.min(total, (page + 1) * pageSize);
  return (
    <div className="flex items-center justify-between border-t px-4 py-3">
      <span className="text-muted-foreground text-sm">
        {start}–{end} of {total}
      </span>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={onPrev}
          disabled={page === 0 || isLoading}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-muted-foreground px-2 text-sm">
          {page + 1} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={onNext}
          disabled={page >= totalPages - 1 || isLoading}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
