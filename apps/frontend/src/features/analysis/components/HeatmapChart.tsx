"use client";

import { useMemo } from "react";
import type { FileHeatmap, Severity } from "@/common/types/contracts";

export interface HeatmapChartProps {
  fileHeatmap: FileHeatmap;
  onLineClick?: (file: string, line: number) => void;
}

const RISK_BADGES: Record<Severity, { bg: string; text: string; label: string }> = {
  critical: { bg: "bg-red-50 border-red-200 text-red-700", text: "text-red-600", label: "Critical" },
  high: { bg: "bg-orange-50 border-orange-200 text-orange-700", text: "text-orange-600", label: "High" },
  medium: { bg: "bg-yellow-50 border-yellow-200 text-yellow-700", text: "text-yellow-600", label: "Medium" },
  low: { bg: "bg-green-50 border-green-200 text-green-700", text: "text-green-600", label: "Low" },
};

const RISK_DOT_COLORS: Record<Severity, string> = {
  critical: "bg-red-500 hover:bg-red-600 ring-red-300",
  high: "bg-orange-500 hover:bg-orange-600 ring-orange-300",
  medium: "bg-yellow-500 hover:bg-yellow-600 ring-yellow-300",
  low: "bg-green-500 hover:bg-green-600 ring-green-300",
};

export function HeatmapChart({ fileHeatmap, onLineClick }: HeatmapChartProps) {
  const sortedFiles = useMemo(() => {
    // Sort files by number of risks (descending)
    return Object.keys(fileHeatmap).sort((a, b) => {
      const aLen = fileHeatmap[a]?.length ?? 0;
      const bLen = fileHeatmap[b]?.length ?? 0;
      return bLen - aLen;
    });
  }, [fileHeatmap]);

  const getSeverityCounts = (risks: typeof fileHeatmap[string]) => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    risks.forEach((r) => {
      counts[r.risk_level] = (counts[r.risk_level] || 0) + 1;
    });
    return counts;
  };

  if (sortedFiles.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-neutral-200 p-8 text-center text-xs text-neutral-400">
        No hotspots or code risks detected in this repository.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
          File Risk Hotspots
        </h4>
        <div className="flex items-center gap-3 text-[10px] font-semibold text-neutral-500">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> Critical
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-orange-500" /> High
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-yellow-500" /> Medium
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" /> Low
          </div>
        </div>
      </div>

      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
        {sortedFiles.map((file) => {
          const risks = fileHeatmap[file] || [];
          const counts = getSeverityCounts(risks);

          return (
            <div
              key={file}
              className="bg-white border border-neutral-100 rounded-lg p-4 shadow-sm hover:border-neutral-200 transition-colors"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-neutral-50 pb-2 mb-3">
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-neutral-800 truncate" title={file}>
                    {file}
                  </p>
                </div>
                {/* Severity Count Badges */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  {Object.entries(counts).map(([level, count]) => {
                    if (count === 0) return null;
                    const b = RISK_BADGES[level as Severity];
                    return (
                      <span
                        key={level}
                        className={`text-[9px] font-bold uppercase tracking-wider border rounded px-1.5 py-0.5 ${b.bg}`}
                      >
                        {count} {b.label}
                      </span>
                    );
                  })}
                </div>
              </div>

              {/* Interactive Dots for Risks (acting like a code minimap) */}
              <div>
                <p className="text-[10px] text-neutral-400 mb-2 font-medium">
                  Click on a hotspot node below to locate the issue in source files:
                </p>
                <div className="flex flex-wrap gap-2">
                  {risks
                    .sort((a, b) => a.line - b.line)
                    .map((risk, idx) => {
                      const dotColor = RISK_DOT_COLORS[risk.risk_level];
                      return (
                        <div key={`${risk.line}-${idx}`} className="relative group">
                          <button
                            type="button"
                            onClick={() => onLineClick?.(file, risk.line)}
                            className={`flex items-center gap-1 text-[10px] font-semibold text-white px-2.5 py-1 rounded-md cursor-pointer transition-all duration-150 active:scale-95 focus:outline-none focus:ring-2 focus:ring-offset-1 ${dotColor}`}
                          >
                            Line {risk.line}
                          </button>
                          
                          {/* Tooltip on Hover */}
                          <div className="absolute z-10 bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-3 bg-neutral-900 text-white rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 pointer-events-none">
                            <div className="text-[10px] font-bold border-b border-neutral-800 pb-1 mb-1.5 flex justify-between uppercase tracking-wider">
                              <span className={RISK_BADGES[risk.risk_level].text}>
                                {risk.risk_level}
                              </span>
                              <span>Line {risk.line}</span>
                            </div>
                            <p className="text-[10px] leading-relaxed text-neutral-300">
                              {risk.reason}
                            </p>
                            {risk.metric && (
                              <div className="mt-1.5 text-[8px] bg-neutral-800 px-1 py-0.5 rounded inline-block text-neutral-400">
                                Metric: {risk.metric}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
