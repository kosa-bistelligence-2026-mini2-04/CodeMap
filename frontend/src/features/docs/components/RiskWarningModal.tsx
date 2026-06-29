"use client";

import { AlertTriangle, ShieldCheck, X } from "lucide-react";
import type { DocGuardPatternItem } from "@/common/types/contracts";


// ──────────────────────────────────────────────
// RiskWarningModal — DOCS-GUARD-API-001 탐지 결과 표시
// ──────────────────────────────────────────────
export interface RiskWarningModalProps {
    detectedCount: number;
    detectedPatterns: DocGuardPatternItem[];
    onClose?: () => void;
}
export function RiskWarningModal({
    detectedCount,
    detectedPatterns,
    onClose,
}: RiskWarningModalProps) {
    if (detectedCount === 0) {
        return (
            <div
                className="flex items-center gap-3 rounded-2xl border px-4 py-3"
                style={{
                    borderColor: "color-mix(in srgb, #22c55e 30%, transparent)",
                    background: "color-mix(in srgb, #22c55e 5%, transparent)",
                }}
            >
                <ShieldCheck className="size-4 shrink-0 text-green-400" />
                <p className="text-sm text-green-400">
                    민감정보가 탐지되지 않았습니다.
                </p>
            </div>
        );
    }

    return (
        <div
            className="rounded-2xl border px-4 py-4"
            style={{
                borderColor: "color-mix(in srgb, #f59e0b 30%, transparent)",
                background: "color-mix(in srgb, #f59e0b 6%, transparent)",
            }}
            role="alert"
        >
            {/* 헤더 */}
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                    <AlertTriangle className="size-4 shrink-0 text-amber-400" />
                    <p className="text-sm font-semibold text-amber-300">
                        민감정보 {detectedCount}건 탐지됨
                    </p>
                </div>
                {onClose && (
                    <button
                        type="button"
                        onClick={onClose}
                        className="text-amber-400/60 transition hover:text-amber-300"
                        aria-label="닫기"
                    >
                        <X className="size-4" />
                    </button>
                )}
            </div>

            {/* 탐지 패턴 목록 */}
            {detectedPatterns.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                    {detectedPatterns.map((p, i) => (
                        <li
                            key={`${p.type}-${i}`}
                            className="flex items-center gap-2"
                        >
                            <span
                                className="rounded px-1.5 py-0.5 font-mono text-[10px] font-medium"
                                style={{
                                    background:
                                        "color-mix(in srgb, #f59e0b 15%, transparent)",
                                    color: "#fbbf24",
                                }}
                            >
                                {p.type}
                            </span>
                            <span
                                className="truncate text-xs"
                                style={{ color: "var(--text-muted)" }}
                            >
                                {p.location}
                            </span>
                        </li>
                    ))}
                </ul>
            )}

            <p className="mt-3 text-[11px] leading-5 text-amber-100/60">
                탐지된 항목은 가이드북에서{" "}
                <code className="font-mono">[MASKED]</code>로 대체되었습니다.
            </p>
        </div>
    );
}
