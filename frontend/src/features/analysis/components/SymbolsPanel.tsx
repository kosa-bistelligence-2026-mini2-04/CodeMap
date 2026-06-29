"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import {
  type CodeSymbol,
  type SymbolCategory,
  type SymbolKind,
  symbolCategory,
} from "@/features/analysis/utils/extractSymbols";

interface SymbolsPanelProps {
  symbols: CodeSymbol[];
  activeLine: number | null;
  onSelect: (line: number) => void;
  isDark: boolean;
}

type FilterKey = "all" | SymbolCategory;

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "전체" },
  { key: "class", label: "클래스" },
  { key: "function", label: "함수" },
  { key: "const", label: "상수" },
];

const KIND_BADGE: Record<SymbolKind, { text: string; cls: string }> = {
  class: { text: "C", cls: "text-purple-400" },
  interface: { text: "I", cls: "text-purple-300" },
  enum: { text: "E", cls: "text-purple-300" },
  struct: { text: "S", cls: "text-purple-300" },
  type: { text: "T", cls: "text-teal-300" },
  function: { text: "ƒ", cls: "text-blue-400" },
  method: { text: "m", cls: "text-blue-300" },
  const: { text: "k", cls: "text-amber-400" },
};


export function SymbolsPanel({ symbols, activeLine, onSelect, isDark }: SymbolsPanelProps) {
  const [filter, setFilter] = useState<FilterKey>("all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return symbols.filter((s) => {
      if (filter !== "all" && symbolCategory(s.kind) !== filter) return false;
      if (q && !s.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [symbols, filter, query]);

  return (
    <div
      className={`flex h-full w-56 shrink-0 flex-col border-l ${
        isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-white"
      }`}
    >
      {/* 헤더 */}
      <div
        className={`flex shrink-0 items-center justify-between border-b px-3 py-2 ${
          isDark ? "border-zinc-800" : "border-zinc-200"
        }`}
      >
        <span className={`text-[11px] font-semibold ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>
          Symbols
        </span>
        <span className="text-[9px] text-zinc-500">{filtered.length}</span>
      </div>

      {/* 검색 */}
      <div className={`shrink-0 border-b px-2 py-2 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
        <div
          className={`flex items-center gap-1.5 rounded-md px-2 py-1 ${
            isDark ? "bg-zinc-900" : "bg-zinc-100"
          }`}
        >
          <Search className="size-3 shrink-0 text-zinc-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="심볼 검색"
            aria-label="심볼 검색"
            className={`min-w-0 flex-1 bg-transparent text-[11px] outline-none ${
              isDark ? "text-zinc-200 placeholder:text-zinc-600" : "text-zinc-800 placeholder:text-zinc-400"
            }`}
          />
        </div>

        {/* 필터 칩 */}
        <div className="mt-2 flex flex-wrap gap-1" role="group" aria-label="심볼 필터">
          {FILTERS.map((f) => {
            const active = filter === f.key;
            return (
              <button
                key={f.key}
                type="button"
                aria-pressed={active}
                onClick={() => setFilter(f.key)}
                className={`rounded px-1.5 py-0.5 text-[9px] font-medium transition ${
                  active
                    ? "bg-blue-500/15 text-blue-400"
                    : isDark
                      ? "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300"
                      : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
                }`}
              >
                {f.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 목록 */}
      <div className="min-h-0 flex-1 overflow-auto py-1">
        {filtered.length === 0 ? (
          <p className="px-3 py-4 text-center text-[10px] text-zinc-500">표시할 심볼이 없습니다.</p>
        ) : (
          <ul>
            {filtered.map((s, i) => {
              const badge = KIND_BADGE[s.kind];
              const active = activeLine === s.line;
              return (
                <li key={`${s.line}-${s.name}-${i}`}>
                  <button
                    type="button"
                    onClick={() => onSelect(s.line)}
                    className={`flex w-full items-center gap-2 px-3 py-1 text-left transition ${
                      active
                        ? isDark
                          ? "bg-blue-500/15"
                          : "bg-blue-50"
                        : isDark
                          ? "hover:bg-zinc-900"
                          : "hover:bg-zinc-100"
                    }`}
                    title={`${s.kind} · L${s.line}`}
                  >
                    <span className={`w-3 shrink-0 text-center font-mono text-[11px] font-bold ${badge.cls}`}>
                      {badge.text}
                    </span>
                    <span
                      className={`min-w-0 flex-1 truncate font-mono text-[11px] ${
                        isDark ? "text-zinc-300" : "text-zinc-700"
                      }`}
                    >
                      {s.name}
                    </span>
                    <span className="shrink-0 font-mono text-[9px] text-zinc-500">{s.line}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
