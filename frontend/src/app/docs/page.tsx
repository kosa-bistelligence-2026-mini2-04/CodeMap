"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { DocGetJsonData } from "@/common/types/contracts";
import { fetchOnboardingDocJson } from "@/features/docs/api/docsApi";
import { GuideViewer } from "@/features/docs/components/GuideViewer";
import { ExportButtons } from "@/features/docs/components/ExportButtons";

function DocsWorkspace() {
  const searchParams = useSearchParams();
  const repoId = searchParams.get("repo_id");

  const [data, setData] = useState<DocGetJsonData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId) return;

    let cancelled = false;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      setData(null);

      try {
        const resp = await fetchOnboardingDocJson(repoId);
        if (!cancelled) setData(resp.data);
      } catch (err: unknown) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "가이드북 조회에 실패했습니다.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [repoId]);

  return (
    <main
      className="min-h-screen px-6 py-16"
      style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}
    >
      <section className="mx-auto flex max-w-5xl flex-col gap-6">
        {/* 헤더 */}
        <div className="flex flex-col gap-1">
          <p
            className="text-xs font-semibold uppercase tracking-[0.24em]"
            style={{ color: "var(--text-muted)" }}
          >
            DOCS-GEN
          </p>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold">온보딩 가이드북</h1>
              <p
                className="mt-1 max-w-xl text-sm leading-6"
                style={{ color: "var(--text-secondary)" }}
              >
                분석 결과로 자동 생성된 신입 개발자용 온보딩 문서를
                섹션별로 확인합니다.
              </p>
            </div>
            <ExportButtons repoId={repoId} />
          </div>
        </div>

        {/* repo_id 미전달 안내 */}
        {!repoId && !isLoading && !data && !error && (
          <div
            className="rounded-2xl border border-dashed px-6 py-4"
            style={{ borderColor: "var(--border-primary)" }}
          >
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              URL에{" "}
              <code
                className="rounded px-1 py-0.5 font-mono text-xs"
                style={{
                  background:
                    "color-mix(in srgb, var(--border-primary) 40%, transparent)",
                }}
              >
                ?repo_id=&lt;UUID&gt;
              </code>{" "}
              파라미터를 전달하면 해당 저장소의 가이드북이 표시됩니다.
            </p>
          </div>
        )}

        {/* 가이드북 뷰어 */}
        <GuideViewer data={data} isLoading={isLoading} error={error} />
      </section>
    </main>
  );
}

export default function DocsPage() {
  return (
    <Suspense
      fallback={
        <div
          className="min-h-screen"
          style={{ background: "var(--bg-primary)" }}
        />
      }
    >
      <DocsWorkspace />
    </Suspense>
  );
}
