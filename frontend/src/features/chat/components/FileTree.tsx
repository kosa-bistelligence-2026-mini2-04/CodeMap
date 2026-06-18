"use client";

import { useMemo, useState } from "react";
import { FileCode2, FileJson2, Search, TestTube2 } from "lucide-react";
import type { WorkspaceFile } from "@/common/types/contracts";
import { useApp } from "@/common/contexts/AppContext";

interface FileTreeProps {
  repoName?: string;
  files?: WorkspaceFile[];
  activeFile?: string | null;
  onFileSelect?: (file: string) => void;
  className?: string;
}

export function FileTree({
  repoName = "현재 프로젝트",
  files = [],
  activeFile,
  onFileSelect,
  className = "",
}: FileTreeProps) {
  const [query, setQuery] = useState("");
  const filteredFiles = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return files.slice(0, 240);
    return files.filter((file) => file.path.toLowerCase().includes(normalized)).slice(0, 240);
  }, [files, query]);

  const { theme } = useApp();
  const isDark = theme === "dark";

  return (
    <aside className={`flex h-full flex-col border-r ${className} ${isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-zinc-50"}`}>
      <div className={`border-b px-3 py-3 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
        <p className="truncate text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">Repository</p>
        <h2 className={`mt-1 truncate text-xs font-semibold ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>{repoName}</h2>
        <label className={`mt-3 flex items-center gap-2 rounded-lg border px-2.5 py-2 ${isDark ? "border-zinc-800 bg-zinc-900/70" : "border-zinc-200 bg-white"}`}>
          <Search className="size-3.5 text-zinc-600" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="파일 검색" className={`min-w-0 flex-1 bg-transparent text-[11px] outline-none ${isDark ? "text-zinc-300 placeholder:text-zinc-600" : "text-zinc-700 placeholder:text-zinc-400"}`} />
        </label>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {filteredFiles.length === 0 ? (
          <div className="px-2 py-8 text-center text-[10px] leading-5 text-zinc-600">
            분석이 완료되면 실제 파일 구조가 여기에 표시됩니다.
          </div>
        ) : (
          <ul className="space-y-0.5">
            {filteredFiles.map((file) => {
              const Icon = file.kind === "test" ? TestTube2 : file.language === "JSON" ? FileJson2 : FileCode2;
              return (
                <li key={file.path}>
                  <button
                    type="button"
                    onClick={() => onFileSelect?.(file.path)}
                    title={file.path}
                    className={`group flex w-full cursor-pointer items-center gap-2 rounded px-2 py-1.5 transition ${
                      activeFile === file.path
                        ? (isDark ? "bg-blue-500/10 text-blue-400" : "bg-blue-50 text-blue-600")
                        : (isDark ? "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200" : "text-zinc-600 hover:bg-zinc-200 hover:text-zinc-900")
                    }`}
                  >
                    <Icon className="size-3.5 shrink-0" />
                    <span className="min-w-0 flex-1 truncate font-mono text-[10px]">{file.path}</span>
                    <span className="text-[8px] text-zinc-700">{file.lines}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <div className="border-t border-zinc-800 px-3 py-2 text-[9px] text-zinc-600">
        {files.length ? `${files.length.toLocaleString()} files indexed` : "No snapshot loaded"}
      </div>
    </aside>
  );
}
