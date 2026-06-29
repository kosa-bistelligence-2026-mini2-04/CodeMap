"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  Github,
  LoaderCircle,
  Menu,
  PanelRightOpen,
  Plus,
  ScanSearch,
  X,
} from "lucide-react";
import { RepoInput } from "@/features/repository/components/RepoInput";
import { HistoryList } from "@/features/history/components/HistoryList";
import { WorkspaceReport } from "@/features/analysis/components/WorkspaceReport";
import { CodeNavigatorPanel } from "@/features/analysis/components/CodeNavigatorPanel";
import { FileTree } from "@/features/chat/components/FileTree";
import { ChatInterface } from "@/features/chat/components/ChatInterface";
import { demoWorkspaceReport } from "@/features/analysis/data/demoWorkspace";
import { getRagIndexBanner } from "@/features/analysis/utils/ragIndexStatus.mjs";
import { useAnalysisJob } from "@/features/analysis/hooks/useAnalysisJob";
import { WorkspaceSelector, type WorkspaceScope } from "@/features/team/components/WorkspaceSelector";
import { useConfirm } from "@/common/hooks/useConfirm";
import { useApp } from "@/common/contexts/AppContext";
import { mergeParseDetails } from "@/features/analysis/utils/mergeParseDetails";

type ViewStatus = "idle" | "running" | "completed" | "failed";

// 모바일 드로워 닫기 모션이 끝난 뒤 데이터 갱신을 트리거하기까지의 디바운스(ms)
const MOBILE_DRAWER_CLOSE_MS = 180;

function AnalyzeWorkspace() {
  const { theme, locale } = useApp();
  const isDark = theme === "dark";
  const isKo = locale === "ko";
  const router = useRouter();
  const searchParams = useSearchParams();
  const preview = searchParams.get("preview") === "1";
  const queryJobId = searchParams.get("job");
  const initialPath = searchParams.get("path") || undefined;
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedLine, setSelectedLine] = useState<number | null>(null);
  const [selectedLineEnd, setSelectedLineEnd] = useState<number | null>(null);
  const [chatPrompt, setChatPrompt] = useState("");
  const [chatPromptNonce, setChatPromptNonce] = useState(0);
  const [mobileChatOpen, setMobileChatOpen] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(searchParams.get("thread"));
  const [workspaceScope, setWorkspaceScope] = useState<WorkspaceScope>("private");
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const [selectedTeamName, setSelectedTeamName] = useState<string | null>(null);
  const { confirm, ConfirmDialog } = useConfirm();
  const {
    jobId,
    job,
    report,
    status,
    error,
    showNewAnalysis,
    setShowNewAnalysis,
    submit,
    selectHistory,
  } = useAnalysisJob({
    preview,
    queryJobId,
    initialReport: preview ? demoWorkspaceReport : null,
    isKo,
    workspaceScope,
    selectedTeamId,
    confirm,
    onRouteJob: (id) => router.replace(`/analyze?job=${id}`),
  });

  // ──────────────────────────────────────────────
  // 모바일 드로워: 닫기 애니메이션과 데이터 갱신 타이밍 분리 (#229)
  // ──────────────────────────────────────────────
  const mobileSelectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (mobileSelectTimer.current) clearTimeout(mobileSelectTimer.current);
    };
  }, []);

  const handleMobileHistorySelect = useCallback(
    (id: string) => {
      // 1) 드로워 닫기 트랜잭션을 먼저 시작한다.
      setMobileSidebarOpen(false);
      // 2) 슬라이드 아웃 모션이 거의 끝난 뒤 데이터 갱신/리렌더를 가동한다.
      if (mobileSelectTimer.current) clearTimeout(mobileSelectTimer.current);
      mobileSelectTimer.current = setTimeout(() => {
        selectHistory(id);
        mobileSelectTimer.current = null;
      }, MOBILE_DRAWER_CLOSE_MS);
    },
    [selectHistory],
  );

  const ask = (prompt: string, contextFile?: string) => {
    if (contextFile) setSelectedFile(contextFile);
    setChatPrompt(prompt);
    setChatPromptNonce((value) => value + 1);
    if (window.matchMedia("(max-width: 1279px)").matches) setMobileChatOpen(true);
  };

  const repoName = report?.repository.name || job?.repoName || "새 프로젝트";
  const progress = preview ? 100 : job?.progress || 0;
  // RAG 인덱스 상태: 'ready' | 'failed' | 'skipped' | 'empty' | undefined
  const ragIndexStatus = job?.report?.rag_index?.status as string | undefined;
  const ragIndexBanner = getRagIndexBanner(ragIndexStatus, locale);
  // chatRepoId: 분석(COMPLETED) 완료 시 활성화. 현재 chat은 키워드 검색 기반으로 임베딩 없이도 동작.
  // ragIndexStatus === 'ready' 일 때는 벡터 검색까지 지원, 그 외에는 키워드 폴백으로 안내.
  const chatRepoId = status === "completed" ? jobId : null;
  const fullChatUrl = preview
    ? "/chat?repo_id=preview-codemap&preview=1"
    : `/chat?repo_id=${jobId || ""}${threadId ? `&thread=${threadId}` : ""}`;
  const workspaceSelector = (
    <WorkspaceSelector
      scope={workspaceScope}
      selectedTeamId={selectedTeamId}
      isDark={isDark}
      isKo={isKo}
      onSelectionChange={({ scope, teamId, teamName }) => {
        setWorkspaceScope(scope);
        setSelectedTeamId(teamId);
        setSelectedTeamName(teamName);
      }}
    />
  );

  return (
    <main className={`flex h-[calc(100vh-3.5rem)] min-h-[640px] flex-col overflow-hidden ${isDark ? "bg-zinc-950 text-white" : "bg-white text-zinc-900"}`}>
      <header className={`flex h-12 shrink-0 items-center gap-3 border-b px-3 md:px-4 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
        <div className="flex min-w-0 items-center gap-2.5">
          <button onClick={() => setMobileSidebarOpen(true)} className="flex items-center justify-center rounded-lg p-1.5 text-zinc-400 transition hover:bg-zinc-900 hover:text-white lg:hidden">
            <Menu className="size-4" />
          </button>
          <div className="hidden size-7 shrink-0 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 lg:flex">
            <Github className="size-3.5 text-zinc-400" />
          </div>
          <div className="min-w-0">
            <p className={`truncate text-xs font-bold ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>{repoName}</p>
            <p className="truncate text-[9px] text-zinc-600">{job ? `${job.owner} / ${job.branch}` : isKo ? "분석과 채팅이 연결되는 저장소 워크스페이스" : "Repository workspace connected with analysis and chat"}</p>
          </div>
        </div>
        {status !== "idle" && (
          <div className="ml-2 hidden items-center gap-2 sm:flex">
            <span className={`size-1.5 rounded-full ${status === "completed" ? "bg-emerald-400" : status === "failed" ? "bg-red-400" : "animate-pulse bg-blue-400"}`} />
            <span className="text-[9px] font-bold uppercase tracking-[0.12em] text-zinc-500">{status === "completed" ? "Ready" : status === "failed" ? "Failed" : `${job?.stage || "Preparing"} · ${progress}%`}</span>
          </div>
        )}
        <div className="ml-auto flex items-center gap-1.5">
          {report && <span className={`hidden rounded-md border px-2 py-1 font-mono text-[8px] md:inline ${isDark ? "border-zinc-800 bg-zinc-900 text-zinc-600" : "border-zinc-200 bg-zinc-100 text-zinc-500"}`}>{preview ? "PREVIEW" : jobId?.slice(0, 8)}</span>}
          <button onClick={() => setShowNewAnalysis(true)} className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[10px] font-semibold transition ${isDark ? "border-zinc-800 text-zinc-400 hover:bg-zinc-900 hover:text-white" : "border-zinc-200 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"}`}><Plus className="size-3" /> {isKo ? "새 분석" : "New Analysis"}</button>
          <button onClick={() => setMobileChatOpen(true)} disabled={!chatRepoId} className={`inline-flex items-center gap-1.5 rounded-lg bg-blue-500 px-2.5 py-1.5 text-[10px] font-bold text-white transition hover:bg-blue-400 disabled:bg-zinc-900 disabled:text-zinc-700 xl:hidden`}><PanelRightOpen className="size-3" /> AI Chat</button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className={`hidden w-[290px] shrink-0 border-r lg:block ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
          {showNewAnalysis || !report ? (
            <div className={`h-full overflow-y-auto p-3 ${isDark ? "bg-zinc-950" : "bg-white"}`}>
              {report && <button onClick={() => setShowNewAnalysis(false)} className={`mb-3 inline-flex items-center gap-1 text-[10px] font-semibold transition ${isDark ? "text-zinc-500 hover:text-white" : "text-zinc-500 hover:text-zinc-900"}`}><ChevronLeft className="size-3" /> {isKo ? "현재 프로젝트로 돌아가기" : "Back to current project"}</button>}
              {workspaceSelector}
              <RepoInput onSubmit={submit} disabled={status === "running"} initialPath={initialPath} initialMode="github" visibility={workspaceScope} selectedTeamId={selectedTeamId} selectedTeamName={selectedTeamName} />
              <div className="mt-3"><HistoryList onSelect={selectHistory} activeJobId={jobId} scope={workspaceScope === "team" ? "team" : "private"} teamId={workspaceScope === "team" ? selectedTeamId : null} /></div>
            </div>
          ) : (
            <div className={`flex h-full min-h-0 flex-col ${isDark ? "bg-zinc-950" : "bg-white"}`}>
              <div className="min-h-0 flex-1">
                <FileTree repoName={repoName} files={report.files} entrypoints={report.entrypoints} activeFile={selectedFile} onFileSelect={setSelectedFile} className="border-r-0" />
              </div>
              <div className={`max-h-[42%] shrink-0 overflow-y-auto border-t p-3 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
                <HistoryList onSelect={selectHistory} activeJobId={jobId} />
              </div>
            </div>
          )}
        </aside>

        <section className={`min-w-0 flex-1 ${selectedFile ? "overflow-hidden" : "overflow-y-auto px-4 py-5 md:px-6 md:py-6"} ${isDark ? "bg-[#0b0b0e]" : "bg-zinc-50"}`}>
          {status === "idle" && (
            <div className="mx-auto flex min-h-full max-w-4xl items-center justify-center py-10">
              <div className="grid w-full gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
                <div>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-500/20 bg-blue-500/10 px-2.5 py-1 text-[10px] font-bold text-blue-300"><ScanSearch className="size-3" /> Repository intelligence workspace</span>
                  <h1 className="mt-5 text-3xl font-bold leading-tight tracking-[-0.04em] md:text-4xl">{isKo ? "분석하고, 바로 질문하고," : "Analyze, question,"}<br /><span className="text-zinc-500">{isKo ? "근거 코드로 돌아오세요." : "return to the code."}</span></h1>
                  <p className="mt-4 max-w-xl text-sm leading-6 text-zinc-500">{isKo ? "저장소의 전체 구조를 한눈에 파악하고, 궁금한 코드는 AI에게 바로 질문하여 깊이 있는 인사이트를 얻어보세요." : "Understand the entire structure at a glance and ask AI questions to gain deep codebase insights."}</p>
                  <button onClick={() => router.push("/analyze?preview=1")} className={`mt-6 inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-xs font-bold transition ${isDark ? "border-zinc-700 bg-zinc-900 text-zinc-200 hover:border-zinc-600 hover:bg-zinc-800" : "border-zinc-300 bg-white text-zinc-800 hover:bg-zinc-50"}`}>{isKo ? "완성된 워크스페이스 미리보기" : "Preview complete workspace"} <ArrowRight className="size-3.5" /></button>
                </div>
                <div className="lg:hidden">{workspaceSelector}<RepoInput onSubmit={submit} disabled={false} initialPath={initialPath} initialMode="github" visibility={workspaceScope} selectedTeamId={selectedTeamId} selectedTeamName={selectedTeamName} /></div>
                <div className={`hidden lg:block rounded-3xl border p-4 shadow-2xl ${isDark ? "border-zinc-800 bg-zinc-900/45 shadow-blue-950/10" : "border-zinc-200 bg-white shadow-zinc-200"}`}>
                  <div className={`flex items-center gap-2 border-b pb-3 ${isDark ? "border-zinc-800" : "border-zinc-100"}`}><span className="size-2 rounded-full bg-emerald-400" /><span className="text-[10px] font-semibold text-zinc-400">{isKo ? "하나의 프로젝트 컨텍스트" : "Unified project context"}</span></div>
                  {(isKo ? ["실제 저장소 구조 분석", "리포트에서 바로 질문", "답변 출처 파일·라인 이동", "패널과 전체 채팅 대화 유지"] : ["Real codebase structure analysis", "Ask questions from reports", "Jump to source file and line", "Maintain full chat context"]).map((item, index) => <div key={item} className={`flex items-center gap-3 border-b py-3 last:border-0 ${isDark ? "border-zinc-800/70" : "border-zinc-100"}`}><span className="flex size-6 items-center justify-center rounded-lg bg-blue-500/10 text-[9px] font-bold text-blue-400">0{index + 1}</span><span className={`text-xs ${isDark ? "text-zinc-400" : "text-zinc-600"}`}>{item}</span><CheckCircle2 className="ml-auto size-3.5 text-emerald-500/70" /></div>)}
                </div>
              </div>
            </div>
          )}

          {status === "running" && (
            <div className="mx-auto flex min-h-full max-w-2xl items-center justify-center">
              <div className={`w-full rounded-2xl border p-6 shadow-xl ${isDark ? "border-zinc-800 bg-zinc-900/55" : "border-zinc-200 bg-white"}`}>
                <div className="flex items-center gap-3"><div className="flex size-10 items-center justify-center rounded-xl bg-blue-500/10"><LoaderCircle className="size-5 animate-spin text-blue-400" /></div><div><h2 className="text-sm font-bold">{job?.status === "COMPLETED" && !job?.report?.rag_index?.status ? (isKo ? "코드 벡터화 진행 중..." : "Vectorizing code context...") : (job?.statusMessage || (isKo ? "저장소 분석 준비 중" : "Preparing analysis"))}</h2><p className="mt-1 text-[10px] text-zinc-500">{job?.status === "COMPLETED" && !job?.report?.rag_index?.status ? (isKo ? "효과적인 RAG 채팅을 위해 분석 결과를 벡터 스토어에 적재하고 있습니다." : "Indexing analysis results to vector store for effective RAG chat.") : (isKo ? "실제 저장소를 복제하고 구조적 근거를 수집하고 있습니다." : "Cloning repository and indexing context.")}</p></div><span className="ml-auto font-mono text-xs font-bold text-blue-400">{progress}%</span></div>
                <div className={`mt-5 h-1.5 overflow-hidden rounded-full ${isDark ? "bg-zinc-800" : "bg-zinc-100"}`}><div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-500" style={{ width: `${Math.max(4, progress)}%` }} /></div>
                <div className="mt-5 grid grid-cols-4 gap-2 text-center text-[9px] font-semibold text-zinc-500">{["Clone", "Code map", "Guide", "Report"].map((step, index) => <div key={step} className={progress >= [5, 28, 72, 95][index] ? "text-blue-400" : ""}>{step}</div>)}</div>
              </div>
            </div>
          )}

          {status === "failed" && (
            <div className="mx-auto flex min-h-full max-w-xl items-center justify-center"><div className="w-full rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-center"><AlertTriangle className="mx-auto size-6 text-red-400" /><h2 className={`mt-3 text-sm font-bold ${isDark ? "" : "text-zinc-800"}`}>{isKo ? "분석을 완료하지 못했습니다" : "Analysis failed"}</h2><p className="mt-2 text-xs leading-5 text-zinc-500">{error}</p><button onClick={() => setShowNewAnalysis(true)} className={`mt-5 rounded-lg px-3 py-2 text-[11px] font-bold ${isDark ? "bg-white text-black" : "bg-zinc-900 text-white"}`}>{isKo ? "입력 확인하기" : "Check input"}</button></div></div>
          )}

          {status === "completed" && report && !selectedFile && ragIndexBanner && (
            <div className={`mx-4 mt-2 flex items-start gap-2 rounded-lg border px-3 py-2 text-[11px] ${
              ragIndexBanner.tone === "error"
                ? "border-red-500/20 bg-red-500/5 text-red-400"
                : "border-yellow-500/20 bg-yellow-500/5 text-yellow-500"
            }`}>
              <AlertTriangle className="mt-0.5 size-3 shrink-0" />
              <span>{ragIndexBanner.message}</span>
            </div>
          )}

          {status === "completed" && report && (
            <div className={`flex min-h-0 gap-0 ${selectedFile ? "h-full" : ""}`}>
              <div className={`min-w-0 ${selectedFile ? "hidden xl:block xl:flex-1" : "flex-1"}`}>
                <WorkspaceReport
                  report={report}
                  preview={preview}
                  onAsk={ask}
                  onFileSelect={(file) => {
                    setSelectedFile(file);
                    setSelectedLine(null);
                    setSelectedLineEnd(null);
                  }}
                />
              </div>
              {selectedFile && jobId && (
                <div className="w-full flex-1 xl:max-w-[880px]">
                  <CodeNavigatorPanel
                    jobId={jobId}
                    filePath={selectedFile}
                    highlightLine={selectedLine}
                    highlightLineEnd={selectedLineEnd}
                    onClose={() => {
                      setSelectedFile(null);
                      setSelectedLine(null);
                      setSelectedLineEnd(null);
                    }}
                  />
                </div>
              )}
            </div>
          )}
        </section>

        <aside className={`hidden w-[400px] shrink-0 border-l xl:block ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
          <ChatInterface
            repoId={chatRepoId}
            repoName={repoName}
            threadId={threadId}
            compact
            preview={preview}
            contextFile={selectedFile}
            initialPrompt={chatPrompt}
            initialPromptKey={chatPromptNonce}
            onThreadChange={setThreadId}
            onReferenceClick={(file, line, lineEnd) => {
              setSelectedFile(file);
              setSelectedLine(line ?? null);
              setSelectedLineEnd(lineEnd ?? null);
            }}
            onClearContextFile={() => setSelectedFile(null)}
            expandHref={fullChatUrl}
          />
        </aside>
      </div>

      {mobileChatOpen && (
        <div className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm xl:hidden" onMouseDown={(event) => { if (event.target === event.currentTarget) setMobileChatOpen(false); }}>
          <div className="absolute inset-y-0 right-0 w-full max-w-[430px] border-l border-zinc-800 bg-zinc-950 shadow-2xl">
            <ChatInterface repoId={chatRepoId} repoName={repoName} threadId={threadId} compact preview={preview} contextFile={selectedFile} initialPrompt={chatPrompt} initialPromptKey={chatPromptNonce} onThreadChange={setThreadId} onReferenceClick={(file, line, lineEnd) => { setSelectedFile(file); setSelectedLine(line ?? null); setSelectedLineEnd(lineEnd ?? null); }} onClearContextFile={() => setSelectedFile(null)} expandHref={fullChatUrl} onClose={() => setMobileChatOpen(false)} />
          </div>
        </div>
      )}

      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm lg:hidden" onMouseDown={(event) => { if (event.target === event.currentTarget) setMobileSidebarOpen(false); }}>
          <div className={`absolute inset-y-0 left-0 flex w-full max-w-[290px] flex-col border-r shadow-2xl ${isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-white"}`}>
            <div className={`flex shrink-0 items-center justify-between border-b px-3 py-2.5 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
              <span className={`text-xs font-bold ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>{isKo ? "탐색기" : "Explorer"}</span>
              <button onClick={() => setMobileSidebarOpen(false)} className={`rounded-lg p-1.5 transition ${isDark ? "text-zinc-500 hover:bg-zinc-900 hover:text-white" : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"}`}><X className="size-4" /></button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto">
              {showNewAnalysis || !report ? (
                <div className="p-3">
                  {report && <button onClick={() => setShowNewAnalysis(false)} className={`mb-3 inline-flex items-center gap-1 text-[10px] font-semibold transition ${isDark ? "text-zinc-500 hover:text-white" : "text-zinc-500 hover:text-zinc-900"}`}><ChevronLeft className="size-3" /> {isKo ? "현재 프로젝트로 돌아가기" : "Back to current project"}</button>}
                  {workspaceSelector}
                  <RepoInput onSubmit={(input) => { submit(input); setMobileSidebarOpen(false); }} disabled={status === "running"} initialPath={initialPath} initialMode="github" visibility={workspaceScope} selectedTeamId={selectedTeamId} selectedTeamName={selectedTeamName} />
                  <div className="mt-3"><HistoryList onSelect={handleMobileHistorySelect} activeJobId={jobId} scope={workspaceScope === "team" ? "team" : "private"} teamId={workspaceScope === "team" ? selectedTeamId : null} /></div>
                </div>
              ) : (
                <div className="flex h-full min-h-0 flex-col">
                  <div className="min-h-0 flex-1">
                    <FileTree repoName={repoName} files={report.files} entrypoints={report.entrypoints} activeFile={selectedFile} onFileSelect={(f) => { setSelectedFile(f); setMobileSidebarOpen(false); }} className="border-r-0" />
                  </div>
                  <div className={`max-h-[42%] shrink-0 overflow-y-auto border-t p-3 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
                    <HistoryList onSelect={handleMobileHistorySelect} activeJobId={jobId} />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog isDark={isDark} isKo={isKo} />
    </main>
  );
}

export default function AnalyzePage() {
  return <Suspense fallback={<div className="h-[calc(100vh-3.5rem)] bg-zinc-950" />}><AnalyzeWorkspace /></Suspense>;
}
