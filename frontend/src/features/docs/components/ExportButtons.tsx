"use client";

import { Download, Printer } from "lucide-react";
import { buildMarkdownDownloadUrl } from "@/features/docs/api/docsApi";

export interface ExportButtonsProps {
  repoId: string | null;
}

export function ExportButtons({ repoId }: ExportButtonsProps) {
  const url = repoId ? buildMarkdownDownloadUrl(repoId) : null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="flex flex-wrap gap-2">
      {/* Markdown 다운로드 — Content-Disposition 헤더 기반 파일 저장 */}
      {url ? (
        <a
          href={url}
          download
          className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition hover:opacity-80"
          style={{
            borderColor: "var(--border-primary)",
            color: "var(--text-secondary)",
          }}
        >
          <Download className="size-3.5" />
          Markdown 다운로드
        </a>
      ) : (
        <button
          type="button"
          disabled
          className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm cursor-not-allowed opacity-40"
          style={{
            borderColor: "var(--border-primary)",
            color: "var(--text-secondary)",
          }}
        >
          <Download className="size-3.5" />
          Markdown 다운로드
        </button>
      )}

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
