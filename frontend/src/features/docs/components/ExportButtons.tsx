"use client";

import { Download } from "lucide-react";
import { buildMarkdownDownloadUrl } from "@/features/docs/api/docsApi";

export interface ExportButtonsProps {
  repoId: string | null;
}

export function ExportButtons({ repoId }: ExportButtonsProps) {
  const url = repoId ? buildMarkdownDownloadUrl(repoId) : null;

  return (
    <div className="flex flex-wrap gap-2">
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
    </div>
  );
}
