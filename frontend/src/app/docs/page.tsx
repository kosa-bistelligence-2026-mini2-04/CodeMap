"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { DocGetJsonData } from "@/common/types/contracts";
import { fetchOnboardingDocJson } from "@/features/docs/api/docsApi";
import { GuideViewer } from "@/features/docs/components/GuideViewer";

function DocsWorkspace() {
    const params = useSearchParams();
    const repoId = params.get("repo_id");

    const [data, setData] = useState<DocGetJsonData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (repoId == null) return;
        let cancelled = false;
        setLoading(true);
        setError(null);
        setData(null);
        fetchOnboardingDocJson(repoId)
            .then((res) => {
                if (!cancelled) setData(res.data);
            })
            .catch((err: unknown) => {
                if (!cancelled)
                    setError(
                        err instanceof Error ? err.message : "알 수 없는 오류"
                    );
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => {
            cancelled = true;
        };
    }, [repoId]);

    if (repoId == null) {
        return (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                repo_id 파라미터가 필요합니다.
            </p>
        );
    }

    if (loading) {
        return (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                가이드북을 불러오는 중…
            </p>
        );
    }

    if (error != null) {
        return (
            <p className="text-sm text-red-400">{error}</p>
        );
    }

    if (data == null) return null;

    return <GuideViewer data={data} />;
}

export default function DocsPage() {
    return (
        <main
            className="min-h-screen px-6 py-24"
            style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}
        >
            <section className="mx-auto flex max-w-5xl flex-col gap-6">
                <header>
                    <p
                        className="text-xs font-semibold uppercase tracking-[0.24em]"
                        style={{ color: "var(--text-muted)" }}
                    >
                        DOCS-GEN
                    </p>
                    <h1 className="mt-1 text-3xl font-bold">가이드북 문서</h1>
                </header>
                <Suspense
                    fallback={
                        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                            로딩 중…
                        </p>
                    }
                >
                    <DocsWorkspace />
                </Suspense>
            </section>
        </main>
    );
}
