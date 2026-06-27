"use client";

import { useEffect, useRef, useState } from "react";
import { Copy, Check, X, AlertTriangle } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";
import { fetchFileContent } from "@/features/analysis/api/api";

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
  const [lines, setLines] = useState(0);
  const [truncated, setTruncated] = useState(false);
  const [copied, setCopied] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const highlightRowRef = useRef<HTMLTableRowElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!filePath) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoadState("loading");
    setContent("");
    setErrorMessage("");
    setCopied(false);

    fetchFileContent(jobId, filePath, controller.signal)
      .then((res) => {
        setContent(res.data.content);
        setLines(res.data.lines);
        setTruncated(res.data.truncated);
        setLoadState("success");
      })
      .catch((err: Error) => {
        if (err.name === "AbortError") return;
        setErrorMessage(err.message);
        setLoadState("error");
      });

    return () => {
      controller.abort();
    };
  }, [jobId, filePath]);

  useEffect(() => {
    if (loadState !== "success") return;
    if (!highlightLine) return;
    highlightRowRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [loadState, highlightLine]);

  const handleCopy = () => {
    void navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const isHighlighted = (lineIndex: number) => {
    if (!highlightLine) return false;
    const start = highlightLine;
    const end = highlightLineEnd ?? highlightLine;
    return lineIndex + 1 >= start && lineIndex + 1 <= end;
  };

  const fileName = filePath.split("/").pop() ?? filePath;
  const codeLines = content.split("\n");

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
        <span
          className={`min-w-0 flex-1 truncate font-mono text-[11px] font-semibold ${
            isDark ? "text-zinc-300" : "text-zinc-700"
          }`}
          title={filePath}
        >
          {fileName}
        </span>
        {highlightLine && (
          <span className="shrink-0 rounded bg-blue-500/10 px-1.5 py-0.5 font-mono text-[9px] font-bold text-blue-400">
            L{highlightLine}
            {highlightLineEnd && highlightLineEnd !== highlightLine
              ? `–${highlightLineEnd}`
              : ""}
          </span>
        )}
        {loadState === "success" && (
          <button
            type="button"
            onClick={handleCopy}
            title="코드 복사"
            className={`shrink-0 rounded p-1 transition ${
              isDark
                ? "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
                : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
            }`}
          >
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          title="닫기"
          className={`shrink-0 rounded p-1 transition ${
            isDark
              ? "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
              : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
          }`}
        >
          <X className="size-3.5" />
        </button>
      </div>

      {/* 경로 서브헤더 */}
      <div
        className={`shrink-0 truncate border-b px-3 py-1 font-mono text-[9px] ${
          isDark
            ? "border-zinc-800/60 text-zinc-600"
            : "border-zinc-100 text-zinc-400"
        }`}
        title={filePath}
      >
        {filePath}
      </div>

      {/* 컨텐츠 영역 */}
      <div className="min-h-0 flex-1 overflow-auto">
        {loadState === "loading" && (
          <div className="flex h-full items-center justify-center">
            <div className="size-5 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
          </div>
        )}

        {loadState === "error" && (
          <div className="flex h-full items-center justify-center px-6">
            <div className="flex flex-col items-center gap-2 text-center">
              <AlertTriangle className="size-5 text-red-400" />
              <p className="text-[11px] text-zinc-500">{errorMessage}</p>
            </div>
          </div>
        )}

        {loadState === "success" && (
          <table className="w-full border-collapse">
            <tbody>
              {codeLines.map((lineText, idx) => {
                const highlighted = isHighlighted(idx);
                return (
                  <tr
                    key={idx}
                    ref={
                      highlightLine && idx + 1 === highlightLine
                        ? highlightRowRef
                        : undefined
                    }
                    className={
                      highlighted
                        ? isDark
                          ? "bg-yellow-400/10"
                          : "bg-yellow-50"
                        : ""
                    }
                  >
                    {/* 줄 번호 */}
                    <td
                      className={`select-none border-r px-2 py-0 text-right font-mono text-[10px] leading-5 ${
                        highlighted
                          ? isDark
                            ? "border-yellow-400/20 text-yellow-400/70"
                            : "border-yellow-200 text-yellow-600"
                          : isDark
                            ? "border-zinc-800 text-zinc-700"
                            : "border-zinc-100 text-zinc-400"
                      }`}
                      style={{ minWidth: "2.75rem" }}
                    >
                      {idx + 1}
                    </td>
                    {/* 코드 내용 */}
                    <td
                      className={`whitespace-pre px-3 py-0 font-mono text-[11px] leading-5 ${
                        highlighted
                          ? isDark
                            ? "text-yellow-100"
                            : "text-zinc-900"
                          : isDark
                            ? "text-zinc-300"
                            : "text-zinc-800"
                      }`}
                    >
                      {lineText}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* 푸터 */}
      {loadState === "success" && (
        <div
          className={`flex shrink-0 items-center justify-between border-t px-3 py-1.5 text-[9px] ${
            isDark
              ? "border-zinc-800 text-zinc-600"
              : "border-zinc-100 text-zinc-400"
          }`}
        >
          <span>{lines.toLocaleString()} 줄</span>
          {truncated && (
            <span className="text-yellow-500">처음 50,000자만 표시됩니다</span>
          )}
        </div>
      )}
    </div>
  );
}
