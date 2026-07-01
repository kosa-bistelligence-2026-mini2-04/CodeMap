"use client";

import { useState } from "react";
import { Download, Printer, LoaderCircle } from "lucide-react";

export interface ExportButtonsProps {
  repoId: string | null;
  markdownContent?: string | null;
  markdownRepoName?: string | null;
  markdownError?: string | null;
  isMarkdownLoading?: boolean;
  onLoadMarkdown?: () => Promise<{ content: string; repoName: string } | null>;
}

export function ExportButtons({
  repoId,
  markdownContent = null,
  markdownRepoName = null,
  markdownError = null,
  isMarkdownLoading = false,
  onLoadMarkdown,
}: ExportButtonsProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [isPrinting, setIsPrinting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const getMarkdownDoc = async () => {
    if (markdownContent && markdownRepoName) {
      return { content: markdownContent, repoName: markdownRepoName };
    }
    return onLoadMarkdown ? onLoadMarkdown() : null;
  };

  const handleMarkdownDownload = async () => {
    if (!repoId) return;
    try {
      setLocalError(null);
      setIsDownloading(true);
      const doc = await getMarkdownDoc();
      if (!doc) return;

      const blob = new Blob([doc.content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const safeRepoName = doc.repoName.replace(/\//g, "-");
      a.download = `${safeRepoName}-guidebook.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setLocalError("마크다운 다운로드에 실패했습니다.");
    } finally {
      setIsDownloading(false);
    }
  };

  const handlePrint = async () => {
    if (!repoId) return;
    try {
      setLocalError(null);
      setIsPrinting(true);
      const doc = await getMarkdownDoc();
      if (!doc) return;
      window.setTimeout(() => window.print(), 0);
    } catch {
      setLocalError("PDF 저장을 위한 문서를 준비하지 못했습니다.");
    } finally {
      setIsPrinting(false);
    }
  };

  const isBusy = isMarkdownLoading || isDownloading || isPrinting;
  const errorMessage = markdownError || localError;

  return (
    <div className="flex flex-col items-start gap-2 sm:items-end">
      <div className="flex flex-wrap gap-2">
        {/* Markdown 다운로드 — Blob 생성 기반 파일 저장 */}
        <button
          type="button"
          onClick={handleMarkdownDownload}
          disabled={!repoId || isBusy}
          className={[
            "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition",
            repoId && !isBusy
              ? "hover:opacity-80"
              : "cursor-not-allowed opacity-40",
          ].join(" ")}
          style={{
            borderColor: "var(--border-primary)",
            color: "var(--text-secondary)",
          }}
        >
          {isDownloading ? (
            <LoaderCircle className="size-3.5 animate-spin" />
          ) : (
            <Download className="size-3.5" />
          )}
          Markdown 다운로드
        </button>

        {/* PDF 저장 — 브라우저 print API */}
        <button
          type="button"
          onClick={handlePrint}
          disabled={!repoId || isBusy}
          className={[
            "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition",
            repoId && !isBusy
              ? "hover:opacity-80"
              : "cursor-not-allowed opacity-40",
          ].join(" ")}
          style={{
            borderColor: "var(--border-primary)",
            color: "var(--text-secondary)",
          }}
        >
          {isPrinting ? (
            <LoaderCircle className="size-3.5 animate-spin" />
          ) : (
            <Printer className="size-3.5" />
          )}
          PDF 저장
        </button>
      </div>
      {errorMessage && (
        <p className="max-w-xs text-xs text-red-400">{errorMessage}</p>
      )}
    </div>
  );
}
