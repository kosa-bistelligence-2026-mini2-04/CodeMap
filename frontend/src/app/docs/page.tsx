"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/features/auth/store/useAuthStore";
import { ApiError } from "@/common/api/error";
import type { DocGetJsonData } from "@/common/types/contracts";
import {
  fetchOnboardingDocJson,
  fetchOnboardingDocMarkdown,
  triggerOnboardingDocGeneration,
} from "@/features/docs/api/docsApi";
import { GuideViewer } from "@/features/docs/components/GuideViewer";
import { ExportButtons } from "@/features/docs/components/ExportButtons";

function DocsWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const repoId = searchParams.get("repo_id");

  const isRestoring = useAuthStore((state) => state.isRestoring);
  const isLoggedIn = useAuthStore((state) => state.isLoggedIn);

  const [data, setData] = useState<DocGetJsonData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generationNotice, setGenerationNotice] = useState<string | null>(null);
  const [markdownRepoId, setMarkdownRepoId] = useState<string | null>(null);
  const [markdownContent, setMarkdownContent] = useState<string | null>(null);
  const [markdownRepoName, setMarkdownRepoName] = useState<string | null>(null);
  const [markdownError, setMarkdownError] = useState<string | null>(null);
  const [isMarkdownLoading, setIsMarkdownLoading] = useState(false);

  const loadMarkdown = useCallback(async () => {
    if (!repoId) return null;
    if (markdownRepoId === repoId && markdownContent && markdownRepoName) {
      return { content: markdownContent, repoName: markdownRepoName };
    }

    setIsMarkdownLoading(true);
    setMarkdownError(null);
    try {
      const resp = await fetchOnboardingDocMarkdown(repoId);
      const nextDoc = {
        content: resp.data.content,
        repoName: resp.data.repoName,
      };
      setMarkdownRepoId(repoId);
      setMarkdownContent(nextDoc.content);
      setMarkdownRepoName(nextDoc.repoName);
      return nextDoc;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "마크다운 문서를 불러오지 못했습니다.";
      setMarkdownError(message);
      return null;
    } finally {
      setIsMarkdownLoading(false);
    }
  }, [markdownContent, markdownRepoId, markdownRepoName, repoId]);

  useEffect(() => {
    if (isRestoring) return;
    if (!isLoggedIn) {
      router.push("/signin");
      return;
    }
    if (!repoId) return;

    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let retryCount = 0;
    let triggerRequested = false;

    const scheduleReload = (load: () => Promise<void>) => {
      retryCount += 1;
      if (retryCount > 40) {
        setIsLoading(false);
        setError("온보딩 가이드북 생성이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.");
        return;
      }

      retryTimer = setTimeout(() => {
        retryTimer = null;
        void load();
      }, 3000);
    };

    const load = async () => {
      setIsLoading(true);
      setError(null);
      if (retryCount === 0) setData(null);

      try {
        const resp = await fetchOnboardingDocJson(repoId);
        if (!cancelled) {
          setData(resp.data);
          setGenerationNotice(null);
          setMarkdownRepoId(null);
          setMarkdownContent(null);
          setMarkdownRepoName(null);
          setMarkdownError(null);
        }
      } catch (err: unknown) {
        if (cancelled) return;

        if (err instanceof ApiError && err.code === "DOCS_NOT_FOUND") {
          try {
            if (!triggerRequested) {
              triggerRequested = true;
              setGenerationNotice("온보딩 가이드북이 없어 자동 생성 중입니다. 완료되면 화면이 갱신됩니다.");
              await triggerOnboardingDocGeneration(repoId);
            } else {
              setGenerationNotice("온보딩 가이드북을 생성 중입니다. 완료되면 화면이 갱신됩니다.");
            }
            scheduleReload(load);
          } catch (triggerErr: unknown) {
            if (
              triggerErr instanceof ApiError &&
              triggerErr.code === "DOCS_GENERATION_IN_PROGRESS"
            ) {
              setGenerationNotice("온보딩 가이드북 생성이 이미 진행 중입니다. 완료되면 화면이 갱신됩니다.");
              scheduleReload(load);
              return;
            }

            setError(
              triggerErr instanceof Error
                ? triggerErr.message
                : "온보딩 가이드북 생성을 시작하지 못했습니다.",
            );
          }
          return;
        }

        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "가이드북 조회에 실패했습니다.",
          );
        }
      } finally {
        if (!cancelled && !retryTimer) setIsLoading(false);
      }
    };

    void load();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [repoId, isRestoring, isLoggedIn, router]);

  if (isRestoring) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: "var(--bg-primary)" }}
      >
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

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
            <ExportButtons
              repoId={repoId}
              markdownContent={markdownContent}
              markdownRepoName={markdownRepoName}
              markdownError={markdownError}
              isMarkdownLoading={isMarkdownLoading}
              onLoadMarkdown={loadMarkdown}
            />
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
        {generationNotice && (
          <div
            className="rounded-2xl border px-6 py-4 text-sm"
            style={{
              borderColor: "var(--border-primary)",
              color: "var(--text-secondary)",
            }}
          >
            {generationNotice}
          </div>
        )}
        <GuideViewer
          data={data}
          isLoading={isLoading}
          error={error}
          markdownContent={markdownContent}
          markdownError={markdownError}
          isMarkdownLoading={isMarkdownLoading}
          onLoadMarkdown={loadMarkdown}
        />
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
