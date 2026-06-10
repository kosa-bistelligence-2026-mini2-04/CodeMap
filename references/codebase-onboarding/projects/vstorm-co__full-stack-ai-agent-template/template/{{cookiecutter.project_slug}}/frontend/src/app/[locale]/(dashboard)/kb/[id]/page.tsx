{% raw %}"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileText,
  Loader2,
  Lock,
  Plug,
  Plus,
  RefreshCw,
  RotateCw,
  Sparkles,
  Trash2,
  Upload,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingState } from "@/components/states";
import { SyncSourceWizard } from "@/components/rag/sync-source-wizard";
import { useKBDetail } from "@/hooks";
import { cn } from "@/lib/utils";
import type { SyncSourceRead } from "@/lib/rag-api";
import type { KBDocument, KBScope } from "@/types";

type Tab = "documents" | "sources";

const SCOPE_META: Record<KBScope, { label: string; icon: LucideIcon }> = {
  personal: { label: "Personal", icon: Lock },
  org: { label: "Organization", icon: Users },
  app: { label: "App-wide", icon: Sparkles },
};

interface KBDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function KBDetailPage({ params }: KBDetailPageProps) {
  const { id } = use(params);
  const {
    kb,
    documents,
    syncSources,
    connectors,
    isLoading,
    isUploading,
    error,
    refresh,
    uploadDocument,
    deleteDocument,
    createSyncSource,
    triggerSyncSource,
    deleteSyncSource,
  } = useKBDetail(id);

  const [tab, setTab] = useState<Tab>("documents");
  const [isDragging, setIsDragging] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [creatingSource, setCreatingSource] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Light polling while any document is still ingesting.
  useEffect(() => {
    const pending = documents.some((d) => d.status === "pending" || d.status === "processing");
    if (!pending) return;
    const interval = setInterval(() => refresh(), 4000);
    return () => clearInterval(interval);
  }, [documents, refresh]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    for (const file of Array.from(files)) {
      try {
        await uploadDocument(file);
      } catch {
        /* toast handled in hook */
      }
    }
  };

  if (isLoading && !kb) return <LoadingState />;
  if (error && !kb) {
    return (
      <div className="text-destructive flex h-64 items-center justify-center text-sm">{error}</div>
    );
  }
  if (!kb) return null;

  const scopeMeta = SCOPE_META[kb.scope];
  const totalChunks = documents.reduce((sum, d) => sum + d.chunk_count, 0);
  const pendingCount = documents.filter(
    (d) => d.status === "pending" || d.status === "processing",
  ).length;
  const latestActivity = documents
    .map((d) => new Date(d.completed_at ?? d.created_at).getTime())
    .reduce((max, t) => Math.max(max, t), 0);

  return (
    <div
      className="relative mx-auto w-full max-w-6xl"
      onDragEnter={(e) => {
        if (e.dataTransfer.types.includes("Files")) {
          dragCounterRef.current += 1;
          setIsDragging(true);
        }
      }}
      onDragLeave={() => {
        dragCounterRef.current = Math.max(0, dragCounterRef.current - 1);
        if (dragCounterRef.current === 0) setIsDragging(false);
      }}
      onDragOver={(e) => {
        if (e.dataTransfer.types.includes("Files")) e.preventDefault();
      }}
      onDrop={(e) => {
        e.preventDefault();
        dragCounterRef.current = 0;
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      {/* Full-page drop overlay */}
      {isDragging && (
        <div className="bg-background/80 fixed inset-0 z-50 flex items-center justify-center backdrop-blur-md">
          <div className="border-brand bg-card relative isolate flex flex-col items-center gap-4 overflow-hidden rounded-3xl border-2 border-dashed px-12 py-16 shadow-2xl">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 -z-10 rounded-3xl"
              style={{
                background:
                  "radial-gradient(circle at center, oklch(from var(--color-brand) l c h / 0.18), transparent 70%)",
              }}
            />
            <span
              className="bg-brand text-brand-foreground flex h-16 w-16 items-center justify-center rounded-2xl"
              style={{ boxShadow: "0 0 40px oklch(from var(--color-brand) l c h / 0.5)" }}
            >
              <Upload className="h-7 w-7" />
            </span>
            <div className="text-center">
              <p className="font-display text-foreground text-2xl font-bold tracking-tight">
                Drop to upload
              </p>
              <p className="text-foreground/65 mt-1 text-sm">
                Files will be added to <span className="text-foreground font-medium">{kb.name}</span>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Breadcrumb */}
      <nav className="text-foreground/55 mb-4 flex items-center gap-1 text-xs">
        <Link
          href="/kb"
          className="hover:text-foreground inline-flex items-center gap-1 transition-colors"
        >
          <ArrowLeft className="h-3 w-3" />
          Knowledge bases
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-foreground/80 truncate">{kb.name}</span>
      </nav>

      {/* Split layout: sidebar + main */}
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* SIDEBAR */}
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <div className="border-foreground/10 bg-foreground/[0.02] relative isolate overflow-hidden rounded-2xl border p-6">
            <div
              aria-hidden
              className="pointer-events-none absolute -top-16 -right-16 -z-10 h-40 w-40 rounded-full blur-3xl"
              style={{
                background:
                  "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.2), transparent 65%)",
              }}
            />

            <div className="flex items-center gap-2">
              <span className="bg-brand/15 text-foreground flex h-9 w-9 items-center justify-center rounded-xl">
                <scopeMeta.icon className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
                  {scopeMeta.label}
                  {kb.is_default && " · Default"}
                </p>
              </div>
            </div>

            <h1 className="font-display text-foreground mt-4 text-xl leading-tight font-bold tracking-tight">
              {kb.name}
            </h1>
            {kb.description && (
              <p className="text-foreground/65 mt-2 text-xs leading-relaxed">{kb.description}</p>
            )}

            {/* Stats list */}
            <dl className="border-foreground/10 mt-6 space-y-2.5 border-t pt-5 text-xs">
              <StatRow label="Documents" value={documents.length} />
              <StatRow label="Vectors" value={totalChunks.toLocaleString()} />
              <StatRow
                label="Last activity"
                value={latestActivity > 0 ? relativeTime(latestActivity) : "—"}
              />
              {pendingCount > 0 && (
                <StatRow
                  label="Pending"
                  value={`${pendingCount} ingesting`}
                  highlight
                />
              )}
            </dl>

            <p className="text-foreground/35 mt-5 truncate font-mono text-[10px] tracking-wider uppercase">
              {kb.collection_name}
            </p>

            <div className="mt-5 flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => refresh()}
                className="gap-1.5"
              >
                <RefreshCw className={cn("h-3.5 w-3.5", isLoading && "animate-spin")} />
                Refresh
              </Button>
            </div>
          </div>
        </aside>

        {/* MAIN */}
        <section className="min-w-0">
          {/* Tabs row */}
          <div className="border-foreground/10 mb-5 flex items-center justify-between border-b">
            <div className="flex items-center gap-1">
              <TabButton
                label="Documents"
                count={documents.length}
                active={tab === "documents"}
                onClick={() => setTab("documents")}
              />
              <TabButton
                label="Sources"
                count={syncSources.length}
                active={tab === "sources"}
                onClick={() => setTab("sources")}
              />
            </div>

            <div className="mb-2 flex items-center gap-2">
              {tab === "documents" && (
                <>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) => handleFiles(e.target.files)}
                    disabled={isUploading}
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    className="bg-foreground text-background hover:bg-foreground/90 group inline-flex items-center gap-2.5 rounded-full py-1.5 pr-1.5 pl-3.5 text-xs font-medium transition-colors disabled:opacity-60"
                  >
                    <span>{isUploading ? "Uploading…" : "Upload"}</span>
                    <span className="bg-brand text-brand-foreground flex h-6 w-6 items-center justify-center rounded-full transition-transform group-hover:rotate-90">
                      {isUploading ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Upload className="h-3 w-3" />
                      )}
                    </span>
                  </button>
                </>
              )}
              {tab === "sources" && connectors.length > 0 && (
                <button
                  type="button"
                  onClick={() => setWizardOpen(true)}
                  className="bg-foreground text-background hover:bg-foreground/90 group inline-flex items-center gap-2.5 rounded-full py-1.5 pr-1.5 pl-3.5 text-xs font-medium transition-colors"
                >
                  <span>Connect</span>
                  <span className="bg-brand text-brand-foreground flex h-6 w-6 items-center justify-center rounded-full transition-transform group-hover:rotate-90">
                    <Plus className="h-3 w-3" />
                  </span>
                </button>
              )}
            </div>
          </div>

          {/* Tab body */}
          {tab === "documents" ? (
            documents.length === 0 ? (
              <EmptyDocs onPickFiles={() => fileInputRef.current?.click()} />
            ) : (
              <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-2xl border">
                {documents.map((doc) => (
                  <DocumentRow key={doc.id} doc={doc} onDelete={() => deleteDocument(doc.id)} />
                ))}
              </ul>
            )
          ) : syncSources.length === 0 ? (
            <EmptySources
              hasConnectors={connectors.length > 0}
              onAdd={() => setWizardOpen(true)}
            />
          ) : (
            <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-2xl border">
              {syncSources.map((source) => (
                <SyncSourceRow
                  key={source.id}
                  source={source}
                  onTrigger={() => triggerSyncSource(source.id)}
                  onDelete={() => deleteSyncSource(source.id)}
                />
              ))}
            </ul>
          )}

          {/* Inline hint: drag anywhere */}
          {tab === "documents" && documents.length > 0 && (
            <p className="text-foreground/35 mt-4 text-center font-mono text-[10px] tracking-wider uppercase">
              Drag files anywhere to add
            </p>
          )}
        </section>
      </div>

      <SyncSourceWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        connectors={connectors}
        collections={[{ name: kb.collection_name }]}
        defaultCollection={kb.collection_name}
        submitting={creatingSource}
        onSubmit={async (data) => {
          setCreatingSource(true);
          try {
            await createSyncSource(data);
            setWizardOpen(false);
          } catch {
            /* toast handled in hook */
          } finally {
            setCreatingSource(false);
          }
        }}
      />
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Sub-components
// ──────────────────────────────────────────────────────────────────────────

function TabButton({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "relative -mb-px inline-flex items-center gap-2 border-b-2 px-1 pt-3 pb-3 text-sm font-medium transition-colors",
        active
          ? "border-brand text-foreground"
          : "text-foreground/55 hover:text-foreground border-transparent",
      )}
    >
      {label}
      <span
        className={cn(
          "rounded-full px-1.5 py-0.5 font-mono text-[10px] tabular-nums",
          active ? "bg-brand/15 text-foreground" : "bg-foreground/8 text-foreground/55",
        )}
      >
        {count}
      </span>
    </button>
  );
}

function StatRow({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">{label}</dt>
      <dd
        className={cn(
          "font-mono tabular-nums",
          highlight ? "text-brand" : "text-foreground",
        )}
      >
        {value}
      </dd>
    </div>
  );
}

function EmptyDocs({ onPickFiles }: { onPickFiles: () => void }) {
  return (
    <div className="border-foreground/10 bg-foreground/[0.02] relative isolate overflow-hidden rounded-2xl border-2 border-dashed p-12 text-center">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 50% 50%, oklch(from var(--color-brand) l c h / 0.08), transparent 70%)",
        }}
      />
      <div className="flex flex-col items-center gap-3">
        <span
          className="bg-brand/15 text-foreground flex h-14 w-14 items-center justify-center rounded-2xl"
          style={{ boxShadow: "0 0 32px oklch(from var(--color-brand) l c h / 0.3)" }}
        >
          <Upload className="h-6 w-6" />
        </span>
        <p className="text-foreground text-sm font-medium">No documents yet</p>
        <p className="text-foreground/55 max-w-xs text-xs">
          Drag files anywhere on this page, or pick from your computer.
        </p>
        <button
          type="button"
          onClick={onPickFiles}
          className="border-foreground/15 hover:border-foreground/40 mt-2 inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-medium transition-colors"
        >
          <Upload className="h-3 w-3" />
          Choose files
        </button>
      </div>
    </div>
  );
}

function EmptySources({ hasConnectors, onAdd }: { hasConnectors: boolean; onAdd: () => void }) {
  return (
    <div className="border-foreground/10 bg-foreground/[0.02] rounded-2xl border border-dashed p-10 text-center">
      <span className="bg-foreground/8 text-foreground/65 mx-auto flex h-12 w-12 items-center justify-center rounded-2xl">
        <Plug className="h-5 w-5" />
      </span>
      <p className="text-foreground mt-3 text-sm font-medium">
        {hasConnectors ? "No sources connected" : "No connectors configured"}
      </p>
      <p className="text-foreground/55 mx-auto mt-1 max-w-sm text-xs">
        {hasConnectors
          ? "Add one to keep this knowledge base in sync automatically."
          : "Configure connectors on the workspace level to start syncing from external sources."}
      </p>
      {hasConnectors && (
        <button
          type="button"
          onClick={onAdd}
          className="border-foreground/15 hover:border-foreground/40 mt-4 inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-medium transition-colors"
        >
          <Plus className="h-3 w-3" />
          Connect source
        </button>
      )}
    </div>
  );
}

function SyncSourceRow({
  source,
  onTrigger,
  onDelete,
}: {
  source: SyncSourceRead;
  onTrigger: () => void;
  onDelete: () => void;
}) {
  const lastSync = source.last_sync_at ? new Date(source.last_sync_at).toLocaleString() : "Never";
  const statusColor =
    source.last_sync_status === "completed"
      ? "text-green-700 bg-green-100 dark:bg-green-900/30 dark:text-green-300"
      : source.last_sync_status === "failed"
        ? "text-red-700 bg-red-100 dark:bg-red-900/30 dark:text-red-300"
        : source.last_sync_status === "running"
          ? "text-blue-700 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300"
          : "text-foreground/65 bg-foreground/8";
  return (
    <li className="hover:bg-foreground/[0.02] flex items-center gap-3 px-4 py-3 transition-colors first:rounded-t-2xl last:rounded-b-2xl">
      <div className="bg-foreground/8 text-foreground/65 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
        <Plug className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-foreground truncate text-sm font-medium">{source.name}</p>
          <span className="border-foreground/15 text-foreground/55 inline-flex shrink-0 items-center rounded-full border px-1.5 py-0.5 font-mono text-[9px] tracking-wider uppercase">
            {source.connector_type}
          </span>
        </div>
        <div className="text-foreground/55 mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-[10px] tracking-wider uppercase">
          <span>last sync · {lastSync}</span>
          {source.schedule_minutes && source.schedule_minutes > 0 && (
            <>
              <span>·</span>
              <span>every {source.schedule_minutes}m</span>
            </>
          )}
        </div>
      </div>
      {source.last_sync_status && (
        <Badge
          title={source.last_error ?? undefined}
          className={cn(
            "inline-flex shrink-0 items-center px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase",
            statusColor,
          )}
        >
          {source.last_sync_status}
        </Badge>
      )}
      <Button
        variant="ghost"
        size="sm"
        className="text-foreground/55 hover:text-foreground h-7 w-7 p-0"
        onClick={onTrigger}
        title="Trigger sync now"
      >
        <RotateCw className="h-3.5 w-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="text-foreground/55 hover:text-destructive h-7 w-7 p-0"
        onClick={() => {
          if (confirm(`Disconnect "${source.name}"?`)) onDelete();
        }}
        title="Remove source"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </li>
  );
}

function DocumentRow({ doc, onDelete }: { doc: KBDocument; onDelete: () => void }) {
  return (
    <li className="hover:bg-foreground/[0.02] flex items-center gap-3 px-4 py-3 transition-colors first:rounded-t-2xl last:rounded-b-2xl">
      <div className="bg-foreground/8 text-foreground/65 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
        <FileText className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-foreground truncate text-sm font-medium" title={doc.filename}>
          {doc.filename}
        </p>
        <div className="text-foreground/55 mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-[10px] tracking-wider uppercase">
          {doc.filesize !== null && <span>{formatBytes(doc.filesize)}</span>}
          {doc.filetype && (
            <>
              <span>·</span>
              <span className="truncate">{doc.filetype}</span>
            </>
          )}
          {doc.chunk_count > 0 && (
            <>
              <span>·</span>
              <span>{doc.chunk_count} chunks</span>
            </>
          )}
        </div>
      </div>
      <StatusBadge status={doc.status} message={doc.error_message} />
      <Button
        variant="ghost"
        size="sm"
        className="text-foreground/55 hover:text-destructive h-7 w-7 p-0"
        onClick={() => {
          if (confirm(`Remove "${doc.filename}" from this knowledge base?`)) onDelete();
        }}
        title="Remove document"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </li>
  );
}

function StatusBadge({ status, message }: { status: string; message: string | null }) {
  const config = {
    completed: {
      Icon: CheckCircle2,
      cls: "text-green-700 bg-green-100 dark:bg-green-900/30 dark:text-green-300",
      label: "Ready",
    },
    processing: {
      Icon: Loader2,
      cls: "text-blue-700 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300",
      label: "Processing",
      spin: true,
    },
    pending: {
      Icon: Clock,
      cls: "text-amber-700 bg-amber-100 dark:bg-amber-900/30 dark:text-amber-300",
      label: "Pending",
    },
    failed: {
      Icon: AlertCircle,
      cls: "text-red-700 bg-red-100 dark:bg-red-900/30 dark:text-red-300",
      label: "Failed",
    },
  } as const;
  const c = (config as Record<string, (typeof config)[keyof typeof config]>)[status] ?? {
    Icon: Clock,
    cls: "text-foreground/65 bg-foreground/8",
    label: status,
    spin: false,
  };
  return (
    <Badge
      title={message ?? undefined}
      className={cn(
        "inline-flex shrink-0 items-center gap-1 px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase",
        c.cls,
      )}
    >
      <c.Icon className={cn("h-3 w-3", "spin" in c && c.spin && "animate-spin")} />
      {c.label}
    </Badge>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  if (d < 30) return `${d}d ago`;
  const mo = Math.floor(d / 30);
  return `${mo}mo ago`;
}
{% endraw %}
