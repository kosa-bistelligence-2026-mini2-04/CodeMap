"use client";

import { useState } from "react";
import { Download, Printer, LoaderCircle } from "lucide-react";
import { fetchOnboardingDocMarkdown } from "@/features/docs/api/docsApi";

export interface ExportButtonsProps {
  repoId: string | null;
}

export function ExportButtons({ repoId }: ExportButtonsProps) {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleMarkdownDownload = async () => {
    if (!repoId) return;
    try {
      setIsDownloading(true);
      const resp = await fetchOnboardingDocMarkdown(repoId);
      const markdownContent = resp.data.content;
      
      const blob = new Blob([markdownContent], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const safeRepoName = resp.data.repoName.replace(/\//g, "-");
      a.download = `${safeRepoName}-guidebook.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("마크다운 다운로드에 실패했습니다.");
    } finally {
      setIsDownloading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="flex flex-wrap gap-2">
      {/* Markdown 다운로드 — Blob 생성 기반 파일 저장 */}
      <button
        type="button"
        onClick={handleMarkdownDownload}
        disabled={!repoId || isDownloading}
        className={[
          "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition",
          repoId && !isDownloading
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
        disabled={!repoId}
        className={[
          "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition",
          repoId
            ? "hover:opacity-80"
            : "cursor-not-allowed opacity-40",
        ].join(" ")}
        style={{
          borderColor: "var(--border-primary)",
          color: "var(--text-secondary)",
        }}
      >
        <Printer className="size-3.5" />
        PDF 저장
      </button>
    </div>
  );
}
