"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy, FileCode2, Loader2, TriangleAlert, X } from "lucide-react";
import { fetchFileContent } from "@/features/analysis/api/api";
import { useApp } from "@/common/contexts/AppContext";


interface CodePreviewPanelProps {
  jobId: string;
  filePath: string;
  onClose: () => void;
}

type LoadState = "idle" | "loading" | "success" | "error";


export function CodePreviewPanel({ jobId, filePath, onClose }: CodePreviewPanelProps) {
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

  useEffect(() => {
    if (!filePath) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoadState("loading");
    setContent("");
    setErrorMsg("");

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

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const fileName = filePath.split("/").at(-1) ?? filePath;

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
            <Loader2 className="size-5 animate-spin text-zinc-500" />
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
                {(content.endsWith("\n") ? content.slice(0, -1).split("\n") : content.split("\n")).map((line, idx) => (
                  <tr key={idx} className="group">
                    <td
                      className={`w-10 select-none pr-3 text-right align-top ${
                        isDark ? "text-zinc-700" : "text-zinc-400"
                      }`}
                    >
                      {idx + 1}
                    </td>
                    <td
                      className={`whitespace-pre-wrap break-all pr-4 ${
                        isDark ? "text-zinc-300" : "text-zinc-700"
                      }`}
                    >
                      {line || " "}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
