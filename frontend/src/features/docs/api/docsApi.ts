import type {
  DocGetJsonResponse,
  DocGetMarkdownResponse,
} from "@/common/types/contracts";
import { parseApiError } from "@/common/api/error";
import { apiPath } from "@/features/analysis/api/api";
import { getAccessToken } from "@/features/auth/utils/tokenMemory";

function authHeader(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * GET /api/gen/docs/{repo_id}?format=markdown
 * 온보딩 가이드북 Markdown 전문 조회 (DOCS-GEN-API-001)
 */
export async function fetchOnboardingDocMarkdown(
  repoId: string,
): Promise<DocGetMarkdownResponse> {
  const resp = await fetch(
    apiPath(`/gen/docs/${repoId}?format=markdown`),
    { headers: authHeader() },
  );
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  return resp.json() as Promise<DocGetMarkdownResponse>;
}

/**
 * GET /api/gen/docs/{repo_id}?format=json
 * 온보딩 가이드북 JSON 구조 조회 (DOCS-GEN-API-001)
 */
export async function fetchOnboardingDocJson(
  repoId: string,
): Promise<DocGetJsonResponse> {
  const resp = await fetch(
    apiPath(`/gen/docs/${repoId}?format=json`),
    { headers: authHeader() },
  );
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  return resp.json() as Promise<DocGetJsonResponse>;
}

/**
 * /api/gen/docs/{repo_id}/download?format=md 다운로드 URL 반환
 * 실제 fetch는 브라우저 anchor 태그로 처리 (DOCS-GEN-API-004)
 */
export function buildMarkdownDownloadUrl(repoId: string): string {
  return apiPath(`/gen/docs/${repoId}/download?format=md`);
}
