"use client";

import { useState, useMemo } from "react";
import type { DocGetJsonData, DocFileSummaryItem } from "@/common/types/contracts";
import { buildFileSummaries } from "../utils/buildFileSummaries";

interface FileSummaryPanelProps {
    docData: DocGetJsonData;
}

export function FileSummaryPanel({ docData }: FileSummaryPanelProps) {
    const [query, setQuery] = useState("");
    const [selected, setSelected] = useState<DocFileSummaryItem | null>(null);

    const files = useMemo(
        () =>
            buildFileSummaries(
                docData.readingOrder,
                docData.dangerFiles,
                docData.folderSummaries
            ),
        [docData]
    );

    const filtered = useMemo(
        () =>
            query.trim()
                ? files.filter((f) =>
                      f.path.toLowerCase().includes(query.toLowerCase())
                  )
                : files,
        [files, query]
    );

    return (
        <div className="flex gap-4">
            <aside className="w-64 flex-shrink-0">
                <input
                    type="text"
                    placeholder="파일 검색..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="mb-3 w-full rounded-lg border px-3 py-2 text-sm"
                    style={{
                        borderColor: "var(--border-primary)",
                        background: "var(--bg-secondary)",
                        color: "var(--text-primary)",
                    }}
                />
                <ul className="max-h-96 space-y-1 overflow-y-auto">
                    {filtered.map((file) => (
                        <li key={file.path}>
                            <button
                                type="button"
                                onClick={() => setSelected(file)}
                                className="w-full rounded-lg px-3 py-2 text-left text-xs transition-colors hover:bg-white/10"
                                style={{
                                    background:
                                        selected?.path === file.path
                                            ? "var(--bg-tertiary)"
                                            : undefined,
                                    color: file.isDanger
                                        ? "#ef4444"
                                        : "var(--text-secondary)",
                                }}
                            >
                                <div className="flex items-center gap-1.5">
                                    {file.isDanger && (
                                        <span title="위험 파일">⚠</span>
                                    )}
                                    {file.priority != null && (
                                        <span className="rounded bg-white/10 px-1 font-mono text-[10px]">
                                            #{file.priority}
                                        </span>
                                    )}
                                    <span className="truncate">{file.fileName}</span>
                                </div>
                                <p
                                    className="mt-0.5 truncate text-[10px]"
                                    style={{ color: "var(--text-muted)" }}
                                >
                                    {file.path}
                                </p>
                            </button>
                        </li>
                    ))}
                    {filtered.length === 0 && (
                        <li
                            className="px-3 py-2 text-xs"
                            style={{ color: "var(--text-muted)" }}
                        >
                            검색 결과 없음
                        </li>
                    )}
                </ul>
            </aside>

            <div
                className="min-h-48 flex-1 rounded-xl border p-4"
                style={{ borderColor: "var(--border-primary)" }}
            >
                {selected == null ? (
                    <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                        왼쪽 목록에서 파일을 선택하면 상세 정보를 표시합니다.
                    </p>
                ) : (
                    <FileDetail item={selected} />
                )}
            </div>
        </div>
    );
}


function FileDetail({ item }: { item: DocFileSummaryItem }) {
    return (
        <div className="space-y-4">
            <div>
                <h3
                    className="text-sm font-semibold"
                    style={{ color: "var(--text-primary)" }}
                >
                    {item.fileName}
                </h3>
                <p
                    className="mt-0.5 font-mono text-xs"
                    style={{ color: "var(--text-muted)" }}
                >
                    {item.path}
                </p>
            </div>

            <div className="flex flex-wrap gap-2">
                {item.priority != null && (
                    <span
                        className="rounded-full border px-2.5 py-0.5 text-xs"
                        style={{
                            borderColor: "var(--border-primary)",
                            color: "var(--text-secondary)",
                        }}
                    >
                        읽기 순서 #{item.priority}
                    </span>
                )}
                {item.isDanger && (
                    <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-xs text-amber-300">
                        ⚠ 위험 파일
                    </span>
                )}
            </div>

            {item.folderSummary != null ? (
                <div>
                    <p
                        className="mb-1 text-xs font-medium"
                        style={{ color: "var(--text-secondary)" }}
                    >
                        폴더 요약
                        {item.folderPath != null && (
                            <span
                                className="ml-1 font-mono font-normal"
                                style={{ color: "var(--text-muted)" }}
                            >
                                ({item.folderPath})
                            </span>
                        )}
                    </p>
                    <p
                        className="text-sm leading-relaxed"
                        style={{ color: "var(--text-primary)" }}
                    >
                        {item.folderSummary}
                    </p>
                </div>
            ) : (
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    이 파일이 속한 폴더 요약 정보가 없습니다.
                </p>
            )}
        </div>
    );
}
