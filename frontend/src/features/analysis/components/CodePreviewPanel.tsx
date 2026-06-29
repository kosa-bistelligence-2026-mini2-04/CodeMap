"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy, FileCode2, Loader2, TriangleAlert, X } from "lucide-react";
import { fetchFileContent } from "@/features/analysis/api/api";
import { useApp } from "@/common/contexts/AppContext";


interface CodePreviewPanelProps {
  jobId: string;
  filePath: string;
  highlightLine?: number | null;
  highlightLineEnd?: number | null;
  onClose: () => void;
}

type LoadState = "idle" | "loading" | "success" | "error";


export function CodePreviewPanel({
  jobId,
  filePath,
  highlightLine,
  highlightLineEnd,
  onClose,
}: CodePreviewPanelProps) {
  const { theme } = useApp();
  const isDark = theme === "dark";

  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [content, setContent] = useState("");
  const [language, setLanguage] = useState<string | null>(null);
  const [lines, setLines] = useState(0);
  const [truncated, setTruncated] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [copied, setCopied] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const highlightRowRef = useRef<HTMLTableRowElement | null>(null);

  useEffect(() => {
    if (!filePath) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadState("loading");
    setContent("");
    setErrorMsg("");
    setCopied(false);

    fetchFileContent(jobId, filePath, controller.signal)
      .then((res) => {
        setContent(res.data.content);
        setLanguage(res.data.language);
        setLines(res.data.lines);
        setTruncated(res.data.truncated);
        setLoadState("success");
      })
      .catch((err: Error) => {
        if (err.name === "AbortError") return;
        setErrorMsg(err.message);
        setLoadState("error");
      });

    return () => {
      controller.abort();
    };
  }, [jobId, filePath]);

  useEffect(() => {
    if (loadState !== "success" || !highlightLine) return;
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    highlightRowRef.current?.scrollIntoView({
      behavior: prefersReducedMotion ? "auto" : "smooth",
      block: "center",
    });
  }, [loadState, highlightLine]);

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const fileName = filePath.split("/").at(-1) ?? filePath;
  const isHighlighted = (lineNumber: number) => {
    if (!highlightLine) return false;
    const end = highlightLineEnd ?? highlightLine;
    return lineNumber >= highlightLine && lineNumber <= end;
  };

  return (
    <div
      className={`flex h-full flex-col overflow-hidden border-l ${
        isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-white"
      }`}
    >
      {/* 헤더 */}
      <div
        className={`flex shrink-0 items-center gap-2 border-b px-3 py-2 ${
          isDark ? "border-zinc-800" : "border-zinc-200"
        }`}
      >
        <FileCode2 className="size-3.5 shrink-0 text-zinc-500" />
        <span
          className={`min-w-0 flex-1 truncate font-mono text-[11px] font-semibold ${
            isDark ? "text-zinc-200" : "text-zinc-800"
          }`}
          title={filePath}
        >
          {fileName}
        </span>
        {loadState === "success" && (
          <span className="shrink-0 text-[9px] text-zinc-500">
            {language ?? "text"} · {lines.toLocaleString()} lines
          </span>
        )}
        {highlightLine && (
          <span className="shrink-0 rounded bg-blue-500/10 px-1.5 py-0.5 font-mono text-[9px] font-bold text-blue-400">
            L{highlightLine}
            {highlightLineEnd && highlightLineEnd !== highlightLine ? `-${highlightLineEnd}` : ""}
          </span>
        )}
        <button
          type="button"
          onClick={handleCopy}
          disabled={loadState !== "success"}
          title="클립보드에 복사"
          aria-label="클립보드에 복사"
          className={`flex size-6 items-center justify-center rounded transition disabled:opacity-30 ${
            isDark ? "text-zinc-500 hover:bg-zinc-800 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
          }`}
        >
          {copied ? (
            <Check className="size-3.5 text-emerald-400" />
          ) : (
            <Copy className="size-3.5" />
          )}
        </button>
        <button
          type="button"
          onClick={onClose}
          title="닫기"
          aria-label="코드 프리뷰 닫기"
          className={`flex size-6 items-center justify-center rounded transition ${
            isDark ? "text-zinc-500 hover:bg-zinc-800 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
          }`}
        >
          <X className="size-3.5" />
        </button>
      </div>

      {/* 경로 표시 */}
      <div
        className={`shrink-0 truncate px-3 py-1 font-mono text-[9px] ${
          isDark ? "text-zinc-600" : "text-zinc-400"
        }`}
        title={filePath}
      >
        {filePath}
      </div>

      {/* 본문 */}
      <div className="min-h-0 flex-1 overflow-auto">
        {loadState === "loading" && (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="size-5 text-zinc-500 motion-safe:animate-spin" />
          </div>
        )}

        {loadState === "error" && (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
            <TriangleAlert className="size-5 text-red-400" />
            <p className="text-xs text-zinc-500">{errorMsg}</p>
          </div>
        )}

        {loadState === "success" && (
          <div className="relative">
            {truncated && (
              <div
                className={`sticky top-0 z-10 px-3 py-1.5 text-[10px] font-medium ${
                  isDark
                    ? "bg-yellow-500/10 text-yellow-400"
                    : "bg-yellow-50 text-yellow-700"
                }`}
              >
                파일이 너무 커서 처음 50,000자만 표시됩니다.
              </div>
            )}
            <table className="w-full border-separate border-spacing-0 font-mono text-[11px] leading-5">
              <tbody>
                {(content.endsWith("\n") ? content.slice(0, -1).split("\n") : content.split("\n")).map((line, idx) => {
                  const lineNumber = idx + 1;
                  const highlighted = isHighlighted(lineNumber);
                  return (
                    <tr
                      key={idx}
                      ref={highlightLine && lineNumber === highlightLine ? highlightRowRef : undefined}
                      className={highlighted ? (isDark ? "bg-yellow-400/10" : "bg-yellow-50") : "group"}
                    >
                      <td
                        className={`w-10 select-none pr-3 text-right align-top ${
                          highlighted
                            ? isDark
                              ? "text-yellow-400/80"
                              : "text-yellow-700"
                            : isDark
                              ? "text-zinc-700"
                              : "text-zinc-400"
                        }`}
                      >
                        {lineNumber}
                      </td>
                      <td
                        className={`whitespace-pre-wrap break-all pr-4 ${
                          highlighted
                            ? isDark
                              ? "text-yellow-100"
                              : "text-zinc-900"
                            : isDark
                              ? "text-zinc-300"
                              : "text-zinc-700"
                        }`}
                      >
                        {line || " "}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
