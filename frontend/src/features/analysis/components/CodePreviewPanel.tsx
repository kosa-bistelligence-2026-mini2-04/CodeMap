"use client";

import { useEffect, useReducer, useRef, useState } from "react";
import { X, AlertTriangle, FileCode, Loader2 } from "lucide-react";
import { fetchFileContent } from "@/features/analysis/api/api";
import type { FileContent } from "@/common/types/contracts";

// ──────────────────────────────────────────────
// 상수
// ──────────────────────────────────────────────
const MAX_LINES_FULL = 5000;

// ──────────────────────────────────────────────
// 라인별 하이라이트 클래스 결정 헬퍼
// ──────────────────────────────────────────────
function isHighlighted(
  lineNo: number,
  highlightLine?: number | null,
  highlightRange?: { start: number; end: number } | null,
): boolean {
  if (highlightRange) {
    return lineNo >= highlightRange.start && lineNo <= highlightRange.end;
  }
  return highlightLine != null && lineNo === highlightLine;
}

// ──────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────
interface CodePreviewPanelProps {
  repoId: string;
  path: string;
  highlightLine?: number | null;
  highlightRange?: { start: number; end: number } | null;
  isDark?: boolean;
  onClose?: () => void;
  /** 외부에서 심볼 데이터 사용을 위해 콜백으로 노출 */
  onContentLoaded?: (content: FileContent) => void;
}

// ──────────────────────────────────────────────
// 파일 로딩 상태 reducer (effect 내 sync setState 방지)
// ──────────────────────────────────────────────
type FetchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: FileContent };

type FetchAction =
  | { type: "LOAD" }
  | { type: "OK"; data: FileContent }
  | { type: "ERR"; message: string };

function fetchReducer(_: FetchState, action: FetchAction): FetchState {
  switch (action.type) {
    case "LOAD": return { status: "loading" };
    case "OK":   return { status: "success", data: action.data };
    case "ERR":  return { status: "error", message: action.message };
  }
}

// ──────────────────────────────────────────────
// CodePreviewPanel
// ──────────────────────────────────────────────
export function CodePreviewPanel({
  repoId,
  path,
  highlightLine,
  highlightRange,
  isDark = true,
  onClose,
  onContentLoaded,
}: CodePreviewPanelProps) {
  const [fetchState, dispatch] = useReducer(fetchReducer, { status: "idle" });
  const lineRefs = useRef<Map<number, HTMLTableRowElement>>(new Map());
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [fadingLines, setFadingLines] = useState<Set<number>>(new Set());

  const content = fetchState.status === "success" ? fetchState.data : null;
  const loading = fetchState.status === "loading";
  const error = fetchState.status === "error" ? fetchState.message : null;

  // 파일 로딩: path 변경 시마다 재조회 (dispatch 한 번으로 초기화 → 룰 준수)
  useEffect(() => {
    if (!repoId || !path) return;
    const controller = new AbortController();
    lineRefs.current.clear();
    dispatch({ type: "LOAD" });
    fetchFileContent(repoId, path, controller.signal)
      .then((data) => {
        dispatch({ type: "OK", data });
        onContentLoaded?.(data);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        dispatch({ type: "ERR", message: err instanceof Error ? err.message : "파일을 불러올 수 없습니다." });
      });
    return () => {
      controller.abort();
    };
  }, [repoId, path]); // eslint-disable-line react-hooks/exhaustive-deps

  // 라인 점프: highlightLine/highlightRange 변경 시 scrollIntoView + 하이라이트
  useEffect(() => {
    const targetLine = highlightLine ?? highlightRange?.start ?? null;
    if (targetLine == null || !content) return;

    const row = lineRefs.current.get(targetLine);
    if (!row) return;

    row.scrollIntoView({ block: "center", behavior: "smooth" });

    // 하이라이트 1.5s 후 페이드 아웃
    if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
    const fadingSet = new Set<number>();
    if (highlightRange) {
      for (let i = highlightRange.start; i <= highlightRange.end; i++) fadingSet.add(i);
    } else if (highlightLine != null) {
      fadingSet.add(highlightLine);
    }
    setFadingLines(new Set()); // 리셋
    highlightTimerRef.current = setTimeout(() => {
      setFadingLines(fadingSet);
    }, 1500);

    return () => {
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
    };
  }, [highlightLine, highlightRange, content]);

  // ── 상태별 렌더 ─────────────────────────────
  const bg = isDark ? "bg-zinc-900" : "bg-white";
  const border = isDark ? "border-zinc-800" : "border-zinc-200";
  const textMuted = isDark ? "text-zinc-500" : "text-zinc-400";
  const textCode = isDark ? "text-zinc-200" : "text-zinc-800";

  const header = (
    <div className={`flex shrink-0 items-center gap-2 border-b px-3 py-2 ${border}`}>
      <FileCode className={`size-3.5 shrink-0 ${textMuted}`} />
      <span className={`min-w-0 flex-1 truncate font-mono text-[11px] font-semibold ${textCode}`}>
        {path}
      </span>
      {content && (
        <span className={`shrink-0 font-mono text-[9px] ${textMuted}`}>
          {content.lineCount.toLocaleString()} lines
          {content.language ? ` · ${content.language}` : ""}
        </span>
      )}
      {onClose && (
        <button
          onClick={onClose}
          className={`ml-1 shrink-0 rounded p-0.5 transition ${isDark ? "text-zinc-500 hover:bg-zinc-800 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-900"}`}
        >
          <X className="size-3.5" />
        </button>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className={`flex h-full flex-col overflow-hidden rounded-lg border ${border} ${bg}`}>
        {header}
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className={`size-5 animate-spin ${textMuted}`} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex h-full flex-col overflow-hidden rounded-lg border ${border} ${bg}`}>
        {header}
        <div className={`flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center ${textMuted}`}>
          <AlertTriangle className="size-5 text-amber-500" />
          <p className="text-xs">{error}</p>
        </div>
      </div>
    );
  }

  if (!content) {
    return (
      <div className={`flex h-full flex-col overflow-hidden rounded-lg border ${border} ${bg}`}>
        {header}
        <div className={`flex flex-1 items-center justify-center text-xs ${textMuted}`}>
          파일을 선택하세요.
        </div>
      </div>
    );
  }

  const lines = content.content.split("\n");
  const isTruncated = lines.length > MAX_LINES_FULL;
  const displayLines = isTruncated ? lines.slice(0, MAX_LINES_FULL) : lines;

  return (
    <div className={`flex h-full flex-col overflow-hidden rounded-lg border ${border} ${bg}`}>
      {header}

      {isTruncated && (
        <div className={`shrink-0 border-b px-3 py-1.5 text-[10px] ${border} ${isDark ? "bg-amber-950/30 text-amber-400" : "bg-amber-50 text-amber-600"}`}>
          파일이 너무 큽니다. 처음 {MAX_LINES_FULL.toLocaleString()}줄만 표시합니다.
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse font-mono text-[12px] leading-5">
          <tbody>
            {displayLines.map((lineText, idx) => {
              const lineNo = idx + 1;
              const highlighted = isHighlighted(lineNo, highlightLine, highlightRange);
              const fading = fadingLines.has(lineNo);

              return (
                <tr
                  key={lineNo}
                  ref={(el) => {
                    if (el) lineRefs.current.set(lineNo, el);
                    else lineRefs.current.delete(lineNo);
                  }}
                  className={`transition-colors duration-500 ${
                    highlighted && !fading
                      ? isDark
                        ? "bg-blue-500/20"
                        : "bg-blue-100"
                      : ""
                  }`}
                >
                  <td
                    className={`w-12 select-none py-0 pl-3 pr-4 text-right align-top ${textMuted}`}
                    style={{ userSelect: "none" }}
                  >
                    {lineNo}
                  </td>
                  <td className={`py-0 pr-4 align-top whitespace-pre ${textCode}`}>
                    {lineText || " "}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
