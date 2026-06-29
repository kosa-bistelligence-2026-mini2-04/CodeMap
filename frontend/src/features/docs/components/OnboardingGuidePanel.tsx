"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle, Circle } from "lucide-react";
import type {
    DocReadingOrderItem,
    DocDangerFileItem,
} from "@/common/types/contracts";


// ──────────────────────────────────────────────
// ReadingChecklist — 추천 읽기 순서 체크리스트
// ──────────────────────────────────────────────
function ReadingChecklist({
    items,
    checked,
    onToggle,
}: {
    items: DocReadingOrderItem[];
    checked: Set<string>;
    onToggle: (path: string) => void;
}) {
    if (items.length === 0) {
        return (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                추천 읽기 순서 정보가 없습니다.
            </p>
        );
    }

    const done = items.filter((i) => checked.has(i.path)).length;

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <span
                    className="text-xs font-semibold"
                    style={{ color: "var(--text-muted)" }}
                >
                    진행 현황
                </span>
                <span
                    className="rounded-full px-2 py-0.5 text-[11px] font-medium"
                    style={{
                        background:
                            "color-mix(in srgb, var(--accent-primary) 12%, transparent)",
                        color: "var(--accent-primary)",
                    }}
                >
                    {done} / {items.length} 완료
                </span>
            </div>

            {/* 진행 바 */}
            <div
                className="h-1.5 overflow-hidden rounded-full"
                style={{
                    background:
                        "color-mix(in srgb, var(--border-primary) 60%, transparent)",
                }}
            >
                <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                        width: `${items.length > 0 ? (done / items.length) * 100 : 0}%`,
                        background: "var(--accent-primary)",
                    }}
                />
            </div>

            <ol className="space-y-2 pt-1">
                {items.map((item) => {
                    const isChecked = checked.has(item.path);
                    return (
                        <li key={item.path}>
                            <button
                                type="button"
                                onClick={() => onToggle(item.path)}
                                className="flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-opacity hover:opacity-80"
                                style={{
                                    background: isChecked
                                        ? "color-mix(in srgb, var(--accent-primary) 8%, transparent)"
                                        : "color-mix(in srgb, var(--border-primary) 25%, transparent)",
                                    opacity: isChecked ? 0.65 : 1,
                                }}
                            >
                                {/* 순위 배지 */}
                                <span
                                    className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold"
                                    style={{
                                        background: isChecked
                                            ? "color-mix(in srgb, var(--accent-primary) 20%, transparent)"
                                            : "color-mix(in srgb, var(--accent-primary) 15%, transparent)",
                                        color: "var(--accent-primary)",
                                    }}
                                >
                                    {item.rank}
                                </span>

                                <div className="min-w-0 flex-1">
                                    <span
                                        className="break-all font-mono text-xs leading-5"
                                        style={{
                                            color: isChecked
                                                ? "var(--text-muted)"
                                                : "var(--text-secondary)",
                                            textDecoration: isChecked
                                                ? "line-through"
                                                : "none",
                                        }}
                                    >
                                        {item.path}
                                    </span>
                                    {item.reason && (
                                        <p
                                            className="mt-0.5 text-[11px] leading-5"
                                            style={{ color: "var(--text-muted)" }}
                                        >
                                            {item.reason}
                                        </p>
                                    )}
                                </div>

                                {/* 체크 아이콘 */}
                                {isChecked ? (
                                    <CheckCircle
                                        className="mt-0.5 size-4 shrink-0"
                                        style={{ color: "var(--accent-primary)" }}
                                    />
                                ) : (
                                    <Circle
                                        className="mt-0.5 size-4 shrink-0"
                                        style={{ color: "var(--text-muted)" }}
                                    />
                                )}
                            </button>
                        </li>
                    );
                })}
            </ol>
        </div>
    );
}


// ──────────────────────────────────────────────
// DangerChecklist — 수정 전 주의점 목록
// ──────────────────────────────────────────────
function DangerChecklist({ items }: { items: DocDangerFileItem[] }) {
    if (items.length === 0) {
        return (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                수정 전 주의 파일이 감지되지 않았습니다.
            </p>
        );
    }

    return (
        <ul className="space-y-2">
            {items.map((item) => (
                <li
                    key={item.path}
                    className="rounded-lg px-3 py-2.5"
                    style={{
                        background:
                            "color-mix(in srgb, #f59e0b 6%, transparent)",
                        borderLeft: "2px solid #f59e0b",
                    }}
                >
                    <div className="flex items-start gap-2">
                        <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-400" />
                        <div className="min-w-0">
                            <span
                                className="break-all font-mono text-xs leading-5"
                                style={{ color: "var(--text-secondary)" }}
                            >
                                {item.path}
                            </span>
                            {item.reason && (
                                <p
                                    className="mt-0.5 text-[11px] leading-5"
                                    style={{ color: "var(--text-muted)" }}
                                >
                                    {item.reason}
                                </p>
                            )}
                        </div>
                    </div>
                </li>
            ))}
        </ul>
    );
}


// ──────────────────────────────────────────────
// OnboardingGuidePanel — F-203 온보딩 가이드 패널
// ──────────────────────────────────────────────
export interface OnboardingGuidePanelProps {
    readingOrder: DocReadingOrderItem[];
    dangerFiles: DocDangerFileItem[];
}
export function OnboardingGuidePanel({
    readingOrder,
    dangerFiles,
}: OnboardingGuidePanelProps) {
    const [checked, setChecked] = useState<Set<string>>(new Set());

    const toggle = (path: string) => {
        setChecked((prev) => {
            const next = new Set(prev);
            if (next.has(path)) next.delete(path);
            else next.add(path);
            return next;
        });
    };

    return (
        <div className="space-y-8">
            {/* 섹션 1: 추천 읽기 순서 체크리스트 */}
            <section className="space-y-3">
                <h3
                    className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest"
                    style={{ color: "var(--text-primary)" }}
                >
                    <span
                        className="inline-block size-1.5 rounded-full"
                        style={{ background: "var(--accent-primary)" }}
                    />
                    추천 읽기 순서
                </h3>
                <ReadingChecklist
                    items={readingOrder}
                    checked={checked}
                    onToggle={toggle}
                />
            </section>

            {/* 구분선 */}
            <div
                className="border-t"
                style={{ borderColor: "var(--border-primary)" }}
            />

            {/* 섹션 2: 수정 전 주의점 */}
            <section className="space-y-3">
                <h3
                    className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest"
                    style={{ color: "var(--text-primary)" }}
                >
                    <span className="inline-block size-1.5 rounded-full bg-amber-400" />
                    수정 전 주의점
                </h3>
                <DangerChecklist items={dangerFiles} />
            </section>
        </div>
    );
}
