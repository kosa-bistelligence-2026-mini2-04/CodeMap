"use client";

import { useState } from "react";
import { Braces, Code2, Package, Puzzle } from "lucide-react";
import type { FileSymbol } from "@/common/types/contracts";

// ──────────────────────────────────────────────
// kind → 배지 색상 + 아이콘 매핑
// ──────────────────────────────────────────────
const KIND_META: Record<string, { label: string; color: string; Icon: React.FC<{ className?: string }> }> = {
  function: {
    label: "fn",
    color: "bg-blue-500/15 text-blue-400 border-blue-500/25",
    Icon: Code2,
  },
  class: {
    label: "class",
    color: "bg-purple-500/15 text-purple-400 border-purple-500/25",
    Icon: Braces,
  },
  module: {
    label: "mod",
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    Icon: Package,
  },
};

function kindMeta(kind: string) {
  return KIND_META[kind] ?? {
    label: kind || "other",
    color: "bg-zinc-700/40 text-zinc-400 border-zinc-600/40",
    Icon: Puzzle,
  };
}

// ──────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────
interface SymbolsPanelProps {
  symbols: FileSymbol[];
  isDark?: boolean;
  onSymbolClick: (startLine: number) => void;
}

// ──────────────────────────────────────────────
// SymbolsPanel
// ──────────────────────────────────────────────
export function SymbolsPanel({ symbols, isDark = true, onSymbolClick }: SymbolsPanelProps) {
  const [filter, setFilter] = useState("");

  const bg = isDark ? "bg-zinc-900" : "bg-white";
  const border = isDark ? "border-zinc-800" : "border-zinc-200";
  const textMuted = isDark ? "text-zinc-500" : "text-zinc-400";
  const textPrimary = isDark ? "text-zinc-200" : "text-zinc-800";
  const hoverRow = isDark ? "hover:bg-zinc-800/70" : "hover:bg-zinc-50";
  const inputBg = isDark ? "bg-zinc-800 border-zinc-700 text-zinc-200 placeholder:text-zinc-600" : "bg-zinc-100 border-zinc-200 text-zinc-800 placeholder:text-zinc-400";

  const filtered = filter.trim()
    ? symbols.filter((s) => s.name.toLowerCase().includes(filter.toLowerCase()))
    : symbols;

  return (
    <div className={`flex h-full flex-col overflow-hidden rounded-lg border ${border} ${bg}`}>
      {/* 헤더 */}
      <div className={`flex shrink-0 items-center gap-2 border-b px-3 py-2 ${border}`}>
        <span className={`flex-1 text-[11px] font-bold ${textPrimary}`}>Symbols</span>
        <span className={`font-mono text-[9px] ${textMuted}`}>{symbols.length}</span>
      </div>

      {/* 필터 입력 */}
      {symbols.length > 6 && (
        <div className={`shrink-0 border-b px-2 py-1.5 ${border}`}>
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter symbols…"
            className={`w-full rounded-md border px-2 py-1 text-[11px] outline-none focus:border-blue-500 ${inputBg}`}
          />
        </div>
      )}

      {/* 심볼 목록 */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className={`flex h-full items-center justify-center text-[11px] ${textMuted}`}>
            {filter ? "일치하는 심볼 없음" : "심볼 없음"}
          </div>
        ) : (
          <ul>
            {filtered.map((sym, idx) => {
              const { label, color, Icon } = kindMeta(sym.kind);
              return (
                <li key={`${sym.name}-${sym.startLine}-${idx}`}>
                  <button
                    onClick={() => onSymbolClick(sym.startLine)}
                    className={`flex w-full items-center gap-2 px-3 py-1.5 text-left transition ${hoverRow}`}
                  >
                    <Icon className={`size-3 shrink-0 ${textMuted}`} />
                    <span className={`min-w-0 flex-1 truncate font-mono text-[11px] ${textPrimary}`}>
                      {sym.name}
                    </span>
                    <span className={`shrink-0 rounded border px-1 py-0.5 text-[8px] font-bold uppercase tracking-wide ${color}`}>
                      {label}
                    </span>
                    <span className={`shrink-0 font-mono text-[9px] ${textMuted}`}>
                      :{sym.startLine}
                    </span>
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
