"use client";

import { useMemo, useState } from "react";
import {
  ChevronRight,
  FileCode2,
  FileJson2,
  Folder,
  FolderOpen,
  Play,
  Search,
  TestTube2,
} from "lucide-react";
import type { WorkspaceFile } from "@/common/types/contracts";
import { useApp } from "@/common/contexts/AppContext";
import {
  buildFileTree,
  getAncestorPaths,
  normalizeRepositoryPath,
  type FileTreeNode,
} from "@/common/utils/fileTree";

interface FileTreeProps {
  repoName?: string;
  files?: WorkspaceFile[];
  entrypoints?: string[];
  activeFile?: string | null;
  onFileSelect?: (file: string) => void;
  className?: string;
}

interface TreeNodesProps {
  nodes: FileTreeNode[];
  depth: number;
  expandedPaths: Set<string>;
  entrypointPaths: Set<string>;
  activeFile?: string | null;
  isDark: boolean;
  onDirectoryToggle: (path: string) => void;
  onFileSelect?: (file: string) => void;
}

function filterTree(nodes: FileTreeNode[], query: string): FileTreeNode[] {
  if (!query) return nodes;

  return nodes.flatMap((node) => {
    if (node.type === "file") {
      return node.path.toLowerCase().includes(query) ? [node] : [];
    }

    const children = filterTree(node.children, query);
    return children.length > 0 ? [{ ...node, children }] : [];
  });
}

function TreeNodes({
  nodes,
  depth,
  expandedPaths,
  entrypointPaths,
  activeFile,
  isDark,
  onDirectoryToggle,
  onFileSelect,
}: TreeNodesProps) {
  return (
    <ul className={depth === 0 ? "space-y-0.5" : ""}>
      {nodes.map((node) => {
        if (node.type === "directory") {
          const isExpanded = expandedPaths.has(node.path);
          const FolderIcon = isExpanded ? FolderOpen : Folder;

          return (
            <li key={node.path}>
              <button
                type="button"
                onClick={() => onDirectoryToggle(node.path)}
                aria-expanded={isExpanded}
                className={`flex w-full items-center gap-1 rounded px-1.5 py-1 text-left transition ${
                  isDark
                    ? "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                    : "text-zinc-600 hover:bg-zinc-200 hover:text-zinc-900"
                }`}
                style={{ paddingLeft: `${depth * 12 + 6}px` }}
              >
                <ChevronRight className={`size-3 shrink-0 transition-transform ${isExpanded ? "rotate-90" : ""}`} />
                <FolderIcon className={`size-3.5 shrink-0 ${isExpanded ? "text-blue-400" : "text-zinc-500"}`} />
                <span className="min-w-0 flex-1 truncate font-mono text-[10px]">{node.name}</span>
              </button>
              {isExpanded && (
                <TreeNodes
                  nodes={node.children}
                  depth={depth + 1}
                  expandedPaths={expandedPaths}
                  entrypointPaths={entrypointPaths}
                  activeFile={activeFile}
                  isDark={isDark}
                  onDirectoryToggle={onDirectoryToggle}
                  onFileSelect={onFileSelect}
                />
              )}
            </li>
          );
        }

        const file = node.file;
        const isEntrypoint = entrypointPaths.has(node.path);
        const Icon = isEntrypoint
          ? Play
          : file?.kind === "test"
            ? TestTube2
            : file?.language === "JSON"
              ? FileJson2
              : FileCode2;

        return (
          <li key={node.path}>
            <button
              type="button"
              onClick={() => onFileSelect?.(node.path)}
              aria-current={activeFile === node.path ? "true" : undefined}
              title={node.path}
              className={`group flex w-full items-center gap-2 rounded px-2 py-1.5 transition ${
                activeFile === node.path
                  ? isDark
                    ? "bg-blue-500/10 text-blue-400"
                    : "bg-blue-50 text-blue-600"
                  : isDark
                    ? "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                    : "text-zinc-600 hover:bg-zinc-200 hover:text-zinc-900"
              }`}
              style={{ paddingLeft: `${depth * 12 + 21}px` }}
            >
              <Icon className={`size-3.5 shrink-0 ${isEntrypoint ? "fill-emerald-400/15 text-emerald-400" : ""}`} />
              <span className="min-w-0 flex-1 truncate font-mono text-[10px]">{node.name}</span>
              {isEntrypoint && (
                <span className="rounded bg-emerald-500/10 px-1 py-0.5 text-[7px] font-bold uppercase tracking-wide text-emerald-400">
                  entry
                </span>
              )}
              <span className="text-[8px] text-zinc-700">{file?.lines}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export function FileTree({
  repoName = "현재 프로젝트",
  files = [],
  entrypoints = [],
  activeFile,
  onFileSelect,
  className = "",
}: FileTreeProps) {
  const [query, setQuery] = useState("");
  const tree = useMemo(() => buildFileTree(files), [files]);
  const entrypointPaths = useMemo(
    () => new Set(entrypoints.map(normalizeRepositoryPath)),
    [entrypoints],
  );
  const normalizedQuery = query.trim().toLowerCase();
  const filteredTree = useMemo(() => filterTree(tree, normalizedQuery), [tree, normalizedQuery]);
  const [directoryStates, setDirectoryStates] = useState<Record<string, boolean>>({});
  const { theme } = useApp();
  const isDark = theme === "dark";

  const expandedPaths = useMemo(() => {
    const paths = new Set(
      tree.filter((node) => node.type === "directory").map((node) => node.path),
    );
    for (const [path, isExpanded] of Object.entries(directoryStates)) {
      if (isExpanded) paths.add(path);
      else paths.delete(path);
    }
    if (activeFile) {
      for (const path of getAncestorPaths(activeFile)) paths.add(path);
    }
    return paths;
  }, [activeFile, directoryStates, tree]);

  const visibleExpandedPaths = useMemo(() => {
    if (!normalizedQuery) return expandedPaths;

    const searchPaths = new Set(expandedPaths);
    const collectDirectories = (nodes: FileTreeNode[]) => {
      for (const node of nodes) {
        if (node.type !== "directory") continue;
        searchPaths.add(node.path);
        collectDirectories(node.children);
      }
    };
    collectDirectories(filteredTree);
    return searchPaths;
  }, [expandedPaths, filteredTree, normalizedQuery]);

  const toggleDirectory = (path: string) => {
    setDirectoryStates((current) => ({
      ...current,
      [path]: !expandedPaths.has(path),
    }));
  };

  return (
    <aside className={`flex h-full flex-col border-r ${className} ${isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-zinc-50"}`}>
      <div className={`border-b px-3 py-3 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
        <p className="truncate text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">Repository</p>
        <h2 className={`mt-1 truncate text-xs font-semibold ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>{repoName}</h2>
        <label className={`mt-3 flex items-center gap-2 rounded-lg border px-2.5 py-2 ${isDark ? "border-zinc-800 bg-zinc-900/70" : "border-zinc-200 bg-white"}`}>
          <Search className="size-3.5 text-zinc-600" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="파일 검색"
            placeholder="파일 검색"
            className={`min-w-0 flex-1 bg-transparent text-[11px] outline-none ${isDark ? "text-zinc-300 placeholder:text-zinc-600" : "text-zinc-700 placeholder:text-zinc-400"}`}
          />
        </label>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {filteredTree.length === 0 ? (
          <div className="px-2 py-8 text-center text-[10px] leading-5 text-zinc-600">
            {files.length === 0 ? "분석이 완료되면 실제 파일 구조가 여기에 표시됩니다." : "일치하는 파일이 없습니다."}
          </div>
        ) : (
          <TreeNodes
            nodes={filteredTree}
            depth={0}
            expandedPaths={visibleExpandedPaths}
            entrypointPaths={entrypointPaths}
            activeFile={activeFile}
            isDark={isDark}
            onDirectoryToggle={toggleDirectory}
            onFileSelect={onFileSelect}
          />
        )}
      </div>
      <div className={`border-t px-3 py-2 text-[9px] text-zinc-600 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
        {files.length ? `${files.length.toLocaleString()} files indexed` : "No snapshot loaded"}
      </div>
    </aside>
  );
}
