"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";
import { ChatInterface } from "@/features/chat/components/ChatInterface";
import { FileTree } from "@/features/chat/components/FileTree";
import { CodePreviewPanel } from "@/features/analysis/components/CodePreviewPanel";
import { SymbolsPanel } from "@/features/analysis/components/SymbolsPanel";
import { fetchJobStatus } from "@/features/analysis/api/api";
import type { FileSymbol, WorkspaceReport } from "@/common/types/contracts";

function ChatContent() {
  const searchParams = useSearchParams();
  const { theme } = useApp();
  const isDark = theme === "dark";
  const repoId = searchParams.get("repo_id") || searchParams.get("job");
  const threadId = searchParams.get("thread");
  const preview = searchParams.get("preview") === "1";
  const [report, setReport] = useState<WorkspaceReport | null>(null);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [activeLine, setActiveLine] = useState<number | null>(null);
  const [previewSymbols, setPreviewSymbols] = useState<FileSymbol[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (!repoId || preview) return;
    let cancelled = false;
    fetchJobStatus(repoId).then((response) => {
      if (!cancelled) setReport(response.data.report || null);
    }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [preview, repoId]);

  const repoName = report?.repository.name || (preview ? "CodeMap" : "현재 프로젝트");
  return (
    <div className={`flex h-[calc(100vh-3.5rem)] w-full flex-col overflow-hidden ${isDark ? "bg-zinc-950 text-white" : "bg-white text-zinc-900"}`}>
      <div className={`flex h-10 shrink-0 items-center gap-2 border-b px-3 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
        <Link href={preview ? "/analyze?preview=1" : `/analyze?job=${repoId || ""}`} className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[10px] font-semibold transition ${isDark ? "text-zinc-500 hover:bg-zinc-900 hover:text-white" : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"}`}>
          <ArrowLeft className="size-3" /> 분석 워크스페이스
        </Link>
        <span className={isDark ? "text-zinc-800" : "text-zinc-300"}>/</span>
        <span className={`truncate text-[10px] font-semibold ${isDark ? "text-zinc-300" : "text-zinc-600"}`}>{repoName}</span>
        <button onClick={() => setSidebarOpen((open) => !open)} className={`ml-auto rounded-md p-1.5 transition ${isDark ? "text-zinc-500 hover:bg-zinc-900 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-900"}`} title="파일 패널 전환">
          {sidebarOpen ? <PanelLeftClose className="size-3.5" /> : <PanelLeftOpen className="size-3.5" />}
        </button>
      </div>
      <div className="flex min-h-0 flex-1">
        {/* 좌측: FileTree */}
        {sidebarOpen && (
          <div className="hidden h-full w-[240px] shrink-0 md:block">
            <FileTree
              repoName={repoName}
              files={report?.files || []}
              entrypoints={report?.entrypoints || []}
              activeFile={activeFile}
              onFileSelect={(f) => { setActiveFile(f); setActiveLine(null); setPreviewSymbols([]); }}
              className="border-r-0"
            />
          </div>
        )}

        {/* 중앙: CodePreview (파일 선택 시) */}
        {activeFile && repoId && !preview && (
          <div className="hidden h-full min-w-0 flex-1 p-2 md:flex md:gap-2">
            <div className="min-w-0 flex-1">
              <CodePreviewPanel
                repoId={repoId}
                path={activeFile}
                highlightLine={activeLine}
                isDark={isDark}
                onClose={() => { setActiveFile(null); setActiveLine(null); setPreviewSymbols([]); }}
                onContentLoaded={(c) => setPreviewSymbols(c.symbols)}
              />
            </div>
            {previewSymbols.length > 0 && (
              <div className="hidden w-[200px] shrink-0 xl:block">
                <SymbolsPanel
                  symbols={previewSymbols}
                  isDark={isDark}
                  onSymbolClick={(line) => setActiveLine(line)}
                />
              </div>
            )}
          </div>
        )}

        {/* 우측: ChatInterface */}
        <div className="h-full min-w-0 flex-1">
          <ChatInterface
            repoId={repoId}
            repoName={repoName}
            threadId={threadId}
            preview={preview}
            contextFile={activeFile}
            onReferenceClick={(file, line) => { setActiveFile(file); setActiveLine(line ?? null); }}
            onClearContextFile={() => { setActiveFile(null); setActiveLine(null); }}
          />
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return <Suspense fallback={<div className="h-[calc(100vh-3.5rem)] w-full" />}><ChatContent /></Suspense>;
}
