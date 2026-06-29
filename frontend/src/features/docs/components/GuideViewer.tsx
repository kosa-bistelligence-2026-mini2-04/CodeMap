"use client";

import type { DocGetJsonData } from "@/common/types/contracts";
import { FileSummaryPanel } from "./FileSummaryPanel";

interface GuideViewerProps {
    data: DocGetJsonData;
}

export function GuideViewer({ data }: GuideViewerProps) {
    return (
        <article
            className="space-y-6 rounded-2xl border p-6"
            style={{ borderColor: "var(--border-primary)" }}
        >
            <header className="flex items-center justify-between">
                <h2
                    className="text-base font-semibold"
                    style={{ color: "var(--text-primary)" }}
                >
                    온보딩 가이드북
                </h2>
                <span
                    className="text-xs"
                    style={{ color: "var(--text-muted)" }}
                >
                    v{data.version} · {new Date(data.generatedAt).toLocaleString("ko-KR")}
                </span>
            </header>

            {data.summary != null && (
                <section>
                    <SectionLabel>프로젝트 요약</SectionLabel>
                    <p
                        className="mt-2 text-sm leading-relaxed"
                        style={{ color: "var(--text-primary)" }}
                    >
                        {data.summary}
                    </p>
                </section>
            )}

            {data.stack.length > 0 && (
                <section>
                    <SectionLabel>기술 스택</SectionLabel>
                    <div className="mt-2 flex flex-wrap gap-2">
                        {data.stack.map((tech) => (
                            <span
                                key={tech}
                                className="rounded-full border px-2.5 py-0.5 text-xs"
                                style={{
                                    borderColor: "var(--border-primary)",
                                    color: "var(--text-secondary)",
                                }}
                            >
                                {tech}
                            </span>
                        ))}
                    </div>
                </section>
            )}

            {data.coreFlow != null && (
                <section>
                    <SectionLabel>핵심 플로우</SectionLabel>
                    <p
                        className="mt-2 text-sm leading-relaxed"
                        style={{ color: "var(--text-primary)" }}
                    >
                        {data.coreFlow}
                    </p>
                </section>
            )}

            <section>
                <SectionLabel>파일 단위 요약</SectionLabel>
                <div className="mt-3">
                    {data.readingOrder.length === 0 &&
                    data.dangerFiles.length === 0 ? (
                        <p
                            className="text-sm"
                            style={{ color: "var(--text-muted)" }}
                        >
                            파일 정보가 없습니다.
                        </p>
                    ) : (
                        <FileSummaryPanel docData={data} />
                    )}
                </div>
            </section>
        </article>
    );
}


function SectionLabel({ children }: { children: React.ReactNode }) {
    return (
        <p
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: "var(--text-muted)" }}
        >
            {children}
        </p>
    );
}
