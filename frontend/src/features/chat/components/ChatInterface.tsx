"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown, Download, Expand, LockKeyhole, MessageSquareText, Send, Trash2, X } from "lucide-react";
import { ModeSelector } from "./ModeSelector";
import { SuggestionChips } from "./SuggestionChips";
import { ChatMessageBubble } from "./ChatMessage";
import { StreamingStatus } from "./StreamingStatus";
import {
  describeStreamTimelineStep,
  fetchThread,
  previewStream,
  streamChat,
  type ChatMessage,
  type ChatMode,
  type StreamPhase,
} from "@/features/chat/api/chatApi";
import { useApp } from "@/common/contexts/AppContext";

interface ChatInterfaceProps {
  repoId?: string | null;
  repoName?: string;
  threadId?: string | null;
  compact?: boolean;
  preview?: boolean;
  initialPrompt?: string;
  initialPromptKey?: number;
  contextFile?: string | null;
  onThreadChange?: (threadId: string) => void;
  onReferenceClick?: (file: string, line?: number | null, lineEnd?: number | null) => void;
  expandHref?: string;
  onClose?: () => void;
  onClearContextFile?: () => void;
}

const generateId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
};

const appendExplorationStep = (
  messages: ChatMessage[],
  assistantId: string,
  step: string,
): ChatMessage[] => messages.map((message) => message.id === assistantId
  ? { ...message, explorationSteps: [...(message.explorationSteps || []), step] }
  : message);

const NEAR_BOTTOM_THRESHOLD_PX = 96;

const isNearScrollBottom = (element: HTMLElement) => (
  element.scrollHeight - element.scrollTop - element.clientHeight <= NEAR_BOTTOM_THRESHOLD_PX
);

export function ChatInterface({
  repoId,
  repoName = "현재 프로젝트",
  threadId,
  compact = false,
  preview = false,
  initialPrompt,
  initialPromptKey,
  contextFile,
  onThreadChange,
  onReferenceClick,
  expandHref,
  onClose,
  onClearContextFile,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<ChatMode>("quick");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamPhase, setStreamPhase] = useState<StreamPhase | null>(null);

  const { theme } = useApp();
  const isDark = theme === "dark";
  const [activeThreadId, setActiveThreadId] = useState<string | null>(threadId || null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollFrameRef = useRef<number | null>(null);
  const shouldAutoScrollRef = useRef(true);
  const userScrollIntentRef = useRef(false);
  const [userPausedScroll, setUserPausedScroll] = useState(false);
  const [showScrollToLatest, setShowScrollToLatest] = useState(false);

  useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    
    const hydrate = async () => {
      if (!cancelled) {
        // 다른 분석 프로젝트로 전환 시 이전 채팅 상태 누수 방지
        setMessages([]);
        setActiveThreadId(threadId || null);
      }

      if (threadId && !preview) {
        const stored = await fetchThread(repoId, threadId);
        if (!cancelled && stored.length) {
          setMessages(stored);
          return;
        }
      }
      const local = window.localStorage.getItem(`codemap-chat:${repoId}`);
      if (!cancelled && local) {
        try {
          setMessages(JSON.parse(local) as ChatMessage[]);
        } catch {
          window.localStorage.removeItem(`codemap-chat:${repoId}`);
        }
      }
    };
    void hydrate();
    return () => { cancelled = true; };
  }, [preview, repoId, threadId]);

  useEffect(() => {
    if (repoId && messages.length) {
      window.localStorage.setItem(`codemap-chat:${repoId}`, JSON.stringify(messages.slice(-80)));
    }
  }, [messages, repoId]);

  useEffect(() => {
    if (!initialPrompt) return;
    const frame = requestAnimationFrame(() => {
      setInput(initialPrompt);
      inputRef.current?.focus();
    });
    return () => cancelAnimationFrame(frame);
  }, [initialPrompt, initialPromptKey]);

  const scrollToLatest = useCallback((behavior: ScrollBehavior = "smooth") => {
    const container = scrollContainerRef.current;
    if (!container) return;
    if (scrollFrameRef.current !== null) {
      cancelAnimationFrame(scrollFrameRef.current);
    }
    const applyBottomScroll = () => {
      if (behavior === "auto") {
        container.scrollTop = container.scrollHeight;
        return;
      }
      container.scrollTo({
        top: Math.max(container.scrollHeight - container.clientHeight, 0),
        behavior,
      });
    };
    scrollFrameRef.current = requestAnimationFrame(() => {
      applyBottomScroll();
      scrollFrameRef.current = requestAnimationFrame(() => {
        applyBottomScroll();
        scrollFrameRef.current = null;
      });
    });
  }, []);

  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const nearBottom = isNearScrollBottom(container);
    if (nearBottom) {
      userScrollIntentRef.current = false;
      shouldAutoScrollRef.current = true;
      setUserPausedScroll(false);
      setShowScrollToLatest(false);
      return;
    }
    if (userScrollIntentRef.current) {
      shouldAutoScrollRef.current = false;
      setUserPausedScroll(true);
      setShowScrollToLatest(messages.length > 0);
    }
  }, [messages.length]);

  const markUserScrollIntent = () => {
    userScrollIntentRef.current = true;
  };

  useEffect(() => {
    return () => {
      if (scrollFrameRef.current !== null) {
        cancelAnimationFrame(scrollFrameRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || !messages.length) return;
    if (userPausedScroll || !shouldAutoScrollRef.current) {
      setShowScrollToLatest(!isNearScrollBottom(container));
      return;
    }
    scrollToLatest(isStreaming ? "auto" : "smooth");
  }, [isStreaming, messages, scrollToLatest, streamPhase, userPausedScroll]);

  const jumpToLatest = () => {
    shouldAutoScrollRef.current = true;
    userScrollIntentRef.current = false;
    setUserPausedScroll(false);
    setShowScrollToLatest(false);
    scrollToLatest("auto");
  };

  const handleSend = useCallback(async (text?: string) => {
    const content = (text || input).trim();
    if (!content || isStreaming || !repoId) return;
    const userMessage: ChatMessage = {
      id: generateId(), role: "user", content, timestamp: Date.now(), mode, contextFile: contextFile || undefined,
    };
    const assistantId = generateId();
    setMessages((current) => [...current, userMessage, {
      id: assistantId, role: "assistant", content: "", timestamp: Date.now(), mode,
    }]);
    shouldAutoScrollRef.current = true;
    userScrollIntentRef.current = false;
    setUserPausedScroll(false);
    setShowScrollToLatest(false);
    setInput("");
    setIsStreaming(true);
    setStreamPhase(null);
    if (inputRef.current) inputRef.current.style.height = "auto";

    const stream = preview
      ? previewStream(content)
      : streamChat(repoId, content, mode, { threadId: activeThreadId, contextFile });
    try {
      for await (const event of stream) {
        const timelineStep = describeStreamTimelineStep(event);
        if (timelineStep) {
          setMessages((current) => appendExplorationStep(current, assistantId, timelineStep));
        }

        // Run 시작
        if (event.type === "graph_started") {
          setStreamPhase("searching");
          if (event.sessionId) {
            setActiveThreadId(event.sessionId);
            onThreadChange?.(event.sessionId);
          }
        }
        // 근거 압축 완료
        if (event.type === "evidence_compacted") {
          setStreamPhase("building_context");
        }
        // Evaluator 충분성 판단
        if (event.type === "evaluator_decision") {
          const status = event.sufficient ? "충분" : "추가 탐색 필요";
          const confidence = typeof event.confidence === "number"
            ? ` · 신뢰도 ${Math.round(event.confidence * 100)}%`
            : "";
          const reason = event.reason ? ` — ${event.reason}` : "";
          const step = `Evaluator 판단: ${status}${confidence}${reason}`;
          setMessages((current) => current.map((message) => message.id === assistantId
            ? { ...message, explorationSteps: [...(message.explorationSteps || []), step] }
            : message));
        }
        // Evaluator가 부족한 근거를 발견해 재계획을 요청
        if (event.type === "replan_started") {
          const iteration = typeof event.iteration === "number" && typeof event.maxIterations === "number"
            ? ` (${event.iteration}/${event.maxIterations})`
            : "";
          const missing = event.missingInfo?.length ? ` 부족: ${event.missingInfo.join(", ")}` : "";
          const hint = event.nextPlanHint ? ` 다음 계획: ${event.nextPlanHint}` : "";
          const step = `Re-plan 시작${iteration}.${missing}${hint}`;
          setMessages((current) => current.map((message) => message.id === assistantId
            ? { ...message, explorationSteps: [...(message.explorationSteps || []), step] }
            : message));
          setStreamPhase("searching");
        }
        // 답변 토큰 스트리밍
        if (event.type === "answer_delta" && event.content) {
          if (streamPhase !== "generating") setStreamPhase("generating");
          setMessages((current) => current.map((message) => message.id === assistantId
            ? { ...message, content: message.content + event.content }
            : message));
        }
        // 참조 파일
        if (event.type === "references" && event.references) {
          setMessages((current) => current.map((message) => message.id === assistantId
            ? { ...message, references: event.references }
            : message));
        }
        // 에러
        if (event.type === "error" || event.type === "failed") {
          setStreamPhase("complete");
          setMessages((current) => current.map((message) => message.id === assistantId
            ? { ...message, content: `⚠️ ${event.error || "응답을 생성하지 못했습니다."}` }
            : message));
        }
        if (event.type === "cancelled") {
          setStreamPhase("complete");
          setMessages((current) => current.map((message) => message.id === assistantId
            ? { ...message, content: message.content || "요청이 취소되었습니다." }
            : message));
        }
        // 완료
        if (event.type === "completed") setStreamPhase("complete");
      }
    } finally {
      setIsStreaming(false);
      window.setTimeout(() => setStreamPhase(null), 900);
    }
  }, [activeThreadId, contextFile, input, isStreaming, mode, onThreadChange, preview, repoId, streamPhase]);

  const clearMessages = () => {
    if (isStreaming) return;
    setMessages([]);
    setActiveThreadId(null);
    shouldAutoScrollRef.current = true;
    userScrollIntentRef.current = false;
    setUserPausedScroll(false);
    setShowScrollToLatest(false);
    if (repoId) window.localStorage.removeItem(`codemap-chat:${repoId}`);
  };

  const exportConversation = () => {
    if (!messages.length) return;
    const body = messages.map((message) => `### ${message.role === "user" ? "User" : "CodeMap AI chat"}\n\n${message.content}`).join("\n\n---\n\n");
    const blob = new Blob([`# ${repoName} conversation\n\n${body}`], { type: "text/markdown" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${repoName.replace(/[^a-z0-9-_]/gi, "-")}-chat.md`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  if (!repoId) {
    return (
      <section className={`flex h-full flex-col ${isDark ? "bg-zinc-950" : "bg-zinc-50"}`}>
        <div className={`border-b px-4 py-3 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}><p className={`text-xs font-bold ${isDark ? "text-zinc-200" : "text-zinc-700"}`}>CodeMap AI chat</p></div>
        <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
          <div className={`flex size-11 items-center justify-center rounded-2xl border ${isDark ? "border-zinc-800 bg-zinc-900" : "border-zinc-200 bg-white"}`}><LockKeyhole className={`size-4 ${isDark ? "text-zinc-500" : "text-zinc-400"}`} /></div>
          <p className={`mt-4 text-xs font-semibold ${isDark ? "text-zinc-300" : "text-zinc-700"}`}>분석할 저장소를 먼저 선택하세요</p>
          <p className={`mt-1.5 text-[10px] leading-5 ${isDark ? "text-zinc-600" : "text-zinc-500"}`}>분석 결과와 실제 파일을 공유하는 프로젝트 전용 채팅이 열립니다.</p>
        </div>
      </section>
    );
  }

  const empty = messages.length === 0;
  return (
    <section className={`relative flex h-full min-h-0 flex-col ${isDark ? "bg-zinc-950 text-white" : "bg-white text-zinc-900"} ${compact ? "" : "h-[calc(100vh-3.5rem)]"}`}>
      <header className={`shrink-0 border-b px-3.5 py-2.5 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2"><MessageSquareText className="size-3.5 shrink-0 text-blue-400" /><h2 className="truncate text-xs font-bold">CodeMap AI chat</h2>{preview && <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[8px] font-bold text-amber-400">PREVIEW</span>}</div>
          <div className="flex items-center gap-1">
          {expandHref && <Link href={expandHref} className={`rounded-lg p-2 transition ${isDark ? "text-zinc-500 hover:bg-zinc-900 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-900"}`} title="전체 화면" aria-label="전체 화면"><Expand className="size-3.5" /></Link>}
          <button onClick={exportConversation} disabled={empty} className={`rounded-lg p-2 transition disabled:opacity-25 ${isDark ? "text-zinc-500 hover:bg-zinc-900 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-900"}`} title="Markdown 내보내기"><Download className="size-3.5" /></button>
          <button onClick={clearMessages} disabled={empty || isStreaming} className={`rounded-lg p-2 transition disabled:opacity-25 ${isDark ? "text-zinc-500 hover:bg-zinc-900 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-900"}`} title="대화 지우기"><Trash2 className="size-3.5" /></button>
          {onClose && <button onClick={onClose} className={`rounded-lg p-2 transition xl:hidden ${isDark ? "text-zinc-500 hover:bg-zinc-900 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-900"}`} title="닫기"><X className="size-4" /></button>}
          </div>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <ModeSelector mode={mode} onChange={setMode} disabled={isStreaming} />
          <p className="min-w-0 flex-1 truncate text-right text-[9px] text-zinc-600">{contextFile ? `Context: ${contextFile}` : repoName}</p>
        </div>
      </header>

      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        onWheel={markUserScrollIntent}
        onTouchMove={markUserScrollIntent}
        onPointerDown={markUserScrollIntent}
        onKeyDown={markUserScrollIntent}
        data-chat-scroll-container
        className="flex-1 overflow-y-auto px-3.5 py-4"
      >
        <div className={`mx-auto flex flex-col gap-6 ${compact ? "max-w-xl" : "max-w-3xl"}`}>
          <AnimatePresence mode="wait">
            {empty ? (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="mb-5 rounded-xl border border-blue-500/15 bg-blue-500/5 p-3">
                  <p className="text-[11px] font-semibold text-blue-300">분석과 같은 컨텍스트를 사용합니다</p>
                  <p className="mt-1 text-[10px] leading-5 text-zinc-500">리포트의 파일·위험 신호·권장사항을 질문하면 실제 코드 출처와 함께 답합니다.</p>
                </div>
                <SuggestionChips onSelect={(question) => void handleSend(question)} />
              </motion.div>
            ) : (
              <motion.div key="messages" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
                {messages.map((message, index) => (
                  <ChatMessageBubble
                    key={message.id}
                    message={message}
                    isStreaming={isStreaming && message.role === "assistant" && index === messages.length - 1}
                    onReferenceClick={onReferenceClick}
                    onSuggestionSelect={(question) => void handleSend(question)}
                  />
                ))}
                {isStreaming && streamPhase && streamPhase !== "complete" && <div className="pl-10"><StreamingStatus phase={streamPhase} /></div>}
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>
      </div>

      <AnimatePresence>
        {showScrollToLatest && (
          <motion.button
            type="button"
            onClick={jumpToLatest}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className={`absolute bottom-[6.75rem] right-4 z-10 inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[10px] font-bold shadow-lg transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
              isDark
                ? "border-blue-400/40 bg-zinc-900/95 text-blue-100 hover:border-blue-300 hover:bg-blue-950"
                : "border-blue-200 bg-white/95 text-blue-700 hover:border-blue-300 hover:bg-blue-50"
            }`}
          >
            <ArrowDown className="size-3" />
            최신 답변
          </motion.button>
        )}
      </AnimatePresence>

      <footer className={`shrink-0 border-t ${isDark ? "border-zinc-800" : "border-zinc-200"} px-3.5 py-3`}>
        <div className={`p-4 ${isDark ? "" : "bg-white"}`}>
          <div className={`relative flex flex-col rounded-xl border p-2 focus-within:ring-1 ${isDark ? "border-zinc-800 bg-zinc-900 focus-within:border-zinc-700 focus-within:ring-zinc-700" : "border-zinc-200 bg-zinc-50 focus-within:border-zinc-300 focus-within:ring-zinc-300"}`}>
            {contextFile && (
              <div className={`mb-2 flex items-center justify-between rounded-lg px-2.5 py-1.5 ${isDark ? "bg-zinc-950" : "bg-white"}`}>
                <div className="flex min-w-0 items-center gap-1.5">
                  <span className={`shrink-0 rounded bg-blue-500/10 px-1 py-0.5 text-[8px] font-bold text-blue-400 ${isDark ? "" : ""}`}>CONTEXT</span>
                  <span className={`truncate font-mono text-[10px] ${isDark ? "text-zinc-400" : "text-zinc-600"}`}>{contextFile}</span>
                </div>
                <button onClick={() => onClearContextFile?.()} className={`shrink-0 rounded p-1 transition ${isDark ? "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"}`}><X className="size-3" /></button>
              </div>
            )}
            <textarea ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void handleSend(); } }} placeholder={isStreaming ? "답변을 생성하는 중입니다..." : "이 저장소에 대해 무엇이든 물어보세요"} disabled={isStreaming} className={`min-h-[44px] w-full resize-none bg-transparent px-2 py-1 text-sm outline-none placeholder:text-zinc-600 disabled:opacity-50 ${isDark ? "text-zinc-200" : "text-zinc-900"}`} rows={Math.min(5, input.split("\n").length || 1)} />
            <div className="mt-2 flex items-center justify-between px-1">
              <span className={`text-[10px] ${isDark ? "text-zinc-600" : "text-zinc-400"}`}>{empty && !contextFile ? "AI가 전체 저장소 구조를 참고하여 답변합니다." : contextFile ? "현재 파일을 참고하여 질문합니다." : "이전 대화 맥락을 포함합니다."}</span>
              <button onClick={() => void handleSend(input)} disabled={!input.trim() || isStreaming} className={`flex size-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 ${isDark ? "" : "disabled:bg-zinc-200 disabled:text-zinc-400"}`}><Send className="size-4" /></button>
            </div>
          </div>
        </div>
        <p className={`mt-1.5 text-center text-[8px] ${isDark ? "text-zinc-700" : "text-zinc-400"}`}>답변의 파일·라인 출처를 확인한 뒤 중요한 변경을 적용하세요.</p>
      </footer>
    </section>
  );
}
