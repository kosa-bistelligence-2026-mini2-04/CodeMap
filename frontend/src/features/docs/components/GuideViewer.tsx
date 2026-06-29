"use client";

import { useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  ChevronRight,
  Folder,
  GitBranch,
  Layers,
  List,
  LoaderCircle,
  ShieldAlert,
} from "lucide-react";
import type {
  DocGetJsonData,
  DocReadingOrderItem,
  DocDangerFileItem,
} from "@/common/types/contracts";

// ── 탭 정의 ────────────────────────────────────────────────────

type TabId =
  | "summary"
  | "stack"
  | "readingOrder"
  | "dangerFiles"
  | "coreFlow"
  | "folderSummaries";

interface Tab {
  id: TabId;
  label: string;
  icon: React.ElementType;
}

const TABS: Tab[] = [
  { id: "summary",         label: "프로젝트 요약", icon: BookOpen    },
  { id: "stack",           label: "기술 스택",      icon: Layers      },
  { id: "readingOrder",    label: "읽기 순서",      icon: List        },
  { id: "dangerFiles",     label: "위험 파일",      icon: ShieldAlert },
  { id: "coreFlow",        label: "핵심 플로우",    icon: GitBranch   },
  { id: "folderSummaries", label: "폴더 요약",      icon: Folder      },
];

// ── 개별 패널 컴포넌트 ─────────────────────────────────────────

function SummaryPanel({ text }: { text: string | null }) {
  if (!text) {
    return (
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        요약 정보가 없습니다.
      </p>
    );
  }
  return (
    <p
      className="whitespace-pre-wrap text-sm leading-7"
      style={{ color: "var(--text-secondary)" }}
    >
      {text}
    </p>
  );
}

function StackPanel({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        기술 스택 정보가 없습니다.
      </p>
    );
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((name) => (
        <span
          key={name}
          className="rounded-full border px-3 py-1 text-xs font-medium"
          style={{
            borderColor: "var(--border-primary)",
            color: "var(--text-secondary)",
          }}
        >
          {name}
        </span>
      ))}
    </div>
  );
}

function ReadingOrderPanel({ items }: { items: DocReadingOrderItem[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        읽기 순서 정보가 없습니다.
      </p>
    );
  }
  return (
    <ol className="space-y-3">
      {items.map((item) => (
        <li key={item.path} className="flex items-start gap-3">
          <span
            className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold"
            style={{
              background:
                "color-mix(in srgb, var(--accent-primary) 15%, transparent)",
              color: "var(--accent-primary)",
            }}
          >
            {item.rank}
          </span>
          <div className="min-w-0">
            <span
              className="break-all font-mono text-xs leading-5"
              style={{ color: "var(--text-secondary)" }}
            >
              {item.path}
            </span>
            {item.reason && (
              <p
                className="mt-0.5 text-[11px] leading-5"
                style={{ color: "var(--text-muted)" }}
              >
                {item.reason}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function DangerFilesPanel({ items }: { items: DocDangerFileItem[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        위험 파일이 감지되지 않았습니다.
      </p>
    );
  }
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.path} className="flex items-start gap-2">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-400" />
          <div className="min-w-0">
            <span
              className="break-all font-mono text-xs leading-5"
              style={{ color: "var(--text-secondary)" }}
            >
              {item.path}
            </span>
            {item.reason && (
              <p
                className="mt-0.5 text-[11px] leading-5"
                style={{ color: "var(--text-muted)" }}
              >
                {item.reason}
              </p>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

function CoreFlowPanel({ text }: { text: string | null }) {
  if (!text) {
    return (
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        핵심 플로우 정보가 없습니다.
      </p>
    );
  }
  return (
    <p
      className="whitespace-pre-wrap text-sm leading-7"
      style={{ color: "var(--text-secondary)" }}
    >
      {text}
    </p>
  );
}

function FolderSummariesPanel({
  items,
}: {
  items: DocGetJsonData["folderSummaries"];
}) {
  const [open, setOpen] = useState<Set<string>>(new Set());

  const toggle = (path: string) => {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  if (items.length === 0) {
    return (
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        폴더 요약 정보가 없습니다.
      </p>
    );
  }

  return (
    <ul className="space-y-1">
      {items.map(({ path, summary }) => (
        <li key={path}>
          <button
            type="button"
            onClick={() => toggle(path)}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left transition hover:opacity-80"
            style={{
              background:
                "color-mix(in srgb, var(--border-primary) 30%, transparent)",
            }}
          >
            <ChevronRight
              className={`size-3.5 shrink-0 transition-transform ${
                open.has(path) ? "rotate-90" : ""
              }`}
              style={{ color: "var(--text-muted)" }}
            />
            <span
              className="truncate font-mono text-xs"
              style={{ color: "var(--text-secondary)" }}
            >
              {path}
            </span>
          </button>
          {open.has(path) && (
            <p
              className="px-8 pb-2 pt-1 text-xs leading-6"
              style={{ color: "var(--text-muted)" }}
            >
              {summary}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}

// ── 메인 컴포넌트 ──────────────────────────────────────────────

export interface GuideViewerProps {
  data: DocGetJsonData | null;
  isLoading: boolean;
  error: string | null;
}

export function GuideViewer({ data, isLoading, error }: GuideViewerProps) {
  const [activeTab, setActiveTab] = useState<TabId>("summary");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoaderCircle
          className="size-6 animate-spin"
          style={{ color: "var(--text-muted)" }}
        />
        <span className="ml-3 text-sm" style={{ color: "var(--text-muted)" }}>
          가이드북을 불러오는 중...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-red-400" />
          <div>
            <p className="text-sm font-semibold text-red-400">
              가이드북을 불러오지 못했습니다
            </p>
            <p className="mt-1 text-xs text-red-400/70">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div
        className="rounded-2xl border border-dashed p-8 text-center"
        style={{ borderColor: "var(--border-primary)" }}
      >
        <BookOpen
          className="mx-auto size-8 opacity-30"
          style={{ color: "var(--text-muted)" }}
        />
        <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>
          URL에 <code className="font-mono text-xs">?repo_id=</code> 파라미터를
          전달하면 온보딩 가이드북이 표시됩니다.
        </p>
      </div>
    );
  }

  const panelContent: Record<TabId, React.ReactNode> = {
    summary:         <SummaryPanel text={data.summary} />,
    stack:           <StackPanel items={data.stack} />,
    readingOrder:    <ReadingOrderPanel items={data.readingOrder} />,
    dangerFiles:     <DangerFilesPanel items={data.dangerFiles} />,
    coreFlow:        <CoreFlowPanel text={data.coreFlow} />,
    folderSummaries: <FolderSummariesPanel items={data.folderSummaries} />,
  };

  return (
    <article
      className="rounded-2xl border"
      style={{ borderColor: "var(--border-primary)" }}
    >
      {/* 탭 바 */}
      <div
        className="flex overflow-x-auto border-b"
        style={{ borderColor: "var(--border-primary)" }}
        role="tablist"
        aria-label="가이드북 섹션"
      >
        {TABS.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${id}`}
              onClick={() => setActiveTab(id)}
              className="flex shrink-0 items-center gap-1.5 border-b-2 px-4 py-3 text-xs font-medium transition-colors"
              style={{
                borderBottomColor: isActive
                  ? "var(--accent-primary)"
                  : "transparent",
                color: isActive ? "var(--text-primary)" : "var(--text-muted)",
              }}
            >
              <Icon className="size-3.5" />
              {label}
            </button>
          );
        })}
      </div>

      {/* 탭 패널 */}
      <div id={`panel-${activeTab}`} role="tabpanel" className="p-6">
        {/* 메타 정보 */}
        <div className="mb-4 flex items-center justify-between">
          <p
            className="text-[10px] font-semibold uppercase tracking-[0.18em]"
            style={{ color: "var(--text-muted)" }}
          >
            {TABS.find((t) => t.id === activeTab)?.label}
          </p>
          <span
            className="rounded-full border px-2 py-0.5 text-[10px]"
            style={{
              borderColor: "var(--border-primary)",
              color: "var(--text-muted)",
            }}
          >
            v{data.version} ·{" "}
            {new Date(data.generatedAt).toLocaleDateString("ko-KR")}
          </span>
        </div>

        {panelContent[activeTab]}
      </div>
    </article>
  );
}
