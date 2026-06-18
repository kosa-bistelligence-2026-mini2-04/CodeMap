import type {
  AnalyzeRequest,
  AnalyzeResponse,
} from "@/common/types/contracts";

const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");
const BASE_URL = `${BASE_PATH}/api`;

export function apiPath(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${BASE_URL}${normalizedPath}`;
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
): Promise<{ code: number; message: string; data: Record<string, unknown> }> {
  const resp = await fetch(apiPath(`/repo/analysis/${jobId}`));
  if (!resp.ok) {
    throw new Error(`Failed to fetch job status: ${resp.status}`);
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
