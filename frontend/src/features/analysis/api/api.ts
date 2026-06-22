import type {
  AnalysisHistoryResponse,
  AnalyzeRequest,
  AnalyzeResponse,
  JobStatusData,
  PreValidateRequest,
  PreValidateResponse,
} from "@/common/types/contracts";

const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");
const BASE_URL = `${BASE_PATH}/api`;

export function apiPath(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${BASE_URL}${normalizedPath}`;
}

function getAuthorizationHeader(): string {
  if (typeof window === "undefined") return "Bearer frontend-client";
  const token = localStorage.getItem("cm-access-token")
    || localStorage.getItem("access_token")
    || localStorage.getItem("accessToken")
    || localStorage.getItem("token")
    || "frontend-client";
  return `Bearer ${token}`;
}

/**
 * POST /api/repo/analysis — 분석 작업 등록
 * Backend returns: { code: 201, message: "created", data: { jobId, ... } }
 */
export async function startAnalysis(
  payload: AnalyzeRequest,
): Promise<AnalyzeResponse> {
  const resp = await fetch(apiPath("/repo/analysis"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": typeof crypto !== "undefined" && typeof crypto.randomUUID === "function" 
        ? crypto.randomUUID() 
        : Math.random().toString(36).substring(2, 15),
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const errData = await resp.json().catch(() => ({}));
    throw new Error(errData?.message || errData?.error || `Failed to start analysis: ${resp.status}`);
  }

  return await resp.json();
}

/**
 * GET /api/repo/analysis/{jobId} — 작업 상태 조회
 * Backend returns: { code: 200, message: "success", data: { jobId, status, ... } }
 */
export async function fetchJobStatus(
  jobId: string,
): Promise<{ code: number; message: string; data: JobStatusData }> {
  const resp = await fetch(apiPath(`/repo/analysis/${jobId}`));
  if (!resp.ok) {
    throw new Error(`Failed to fetch job status: ${resp.status}`);
  }
  return await resp.json();
}

export async function fetchAnalysisHistory(
  page = 1,
  limit = 30,
): Promise<AnalysisHistoryResponse> {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });
  const resp = await fetch(apiPath(`/list/analysis?${params.toString()}`), {
    headers: {
      Authorization: getAuthorizationHeader(),
    },
  });

  // 404(엔드포인트 미구현) / 401(인증 미적용) 상황에서는
  // 에러를 throw하지 않고 빈 목록으로 graceful fallback 처리합니다.
  if (resp.status === 404 || resp.status === 401) {
    return {
      code: resp.status,
      message: "fallback",
      data: { totalCount: 0, page, limit, jobs: [] },
    };
  }

  if (!resp.ok) {
    const errData = await resp.json().catch(() => ({}));
    throw new Error(errData?.message || errData?.detail?.message || `Failed to fetch analysis history: ${resp.status}`);
  }

  return await resp.json();
}

/**
 * GET /api/repo/analysis/{jobId}/events — SSE 이벤트 스트림
 * Returns EventSource URL for SSE streaming
 */
export function buildSseUrl(jobId: string): string {
  return apiPath(`/repo/analysis/${jobId}/events`);
}

/**
 * Build WebSocket URL for real-time progress
 * WS /ws/progress/{jobId}
 */
export function buildWsUrl(wsPath: string): string {
  if (/^wss?:\/\//i.test(wsPath)) return wsPath;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const path = wsPath.startsWith("/") ? wsPath : `/${wsPath}`;
  return `${proto}//${host}${BASE_PATH}${path}`;
}

/**
 * POST /api/list/validate — 저장소 사전 검증
 */
export async function validateRepository(
  payload: PreValidateRequest,
): Promise<PreValidateResponse> {
  const resp = await fetch(apiPath("/list/validate"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: getAuthorizationHeader(),
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const errData = await resp.json().catch(() => ({}));
    // CodeMapException의 JSON 구조인 code, error, message를 적절히 파싱합니다.
    throw new Error(errData?.message || errData?.error || `저장소 사전 검증에 실패했습니다. (HTTP ${resp.status})`);
  }

  return await resp.json();
}

