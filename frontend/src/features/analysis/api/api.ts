import type {
  AnalysisHistoryResponse,
  AnalyzeRequest,
  AnalyzeResponse,
  JobStatusData,
  ParseCodeMapData,
  ParseDetails,
  ParseReadmeData,
  ParseStackData,
  ParseSummaryData,
  ParseTreeData,
  PreValidateRequest,
  PreValidateResponse,
  TeamWorkspace,
  TeamInviteItem,
} from "@/common/types/contracts";
import { getAccessToken } from "@/features/auth/utils/tokenMemory";
import { parseApiError } from "@/common/api/error";


const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");
const BASE_URL = `${BASE_PATH}/api`;

export function apiPath(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${BASE_URL}${normalizedPath}`;
}

function getAuthorizationHeaders(): HeadersInit {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
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
      ...getAuthorizationHeaders(),
      "X-Request-Id": typeof crypto !== "undefined" && typeof crypto.randomUUID === "function" 
        ? crypto.randomUUID() 
        : Math.random().toString(36).substring(2, 15),
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    throw await parseApiError(resp);
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
  const resp = await fetch(apiPath(`/repo/analysis/${jobId}`), {
    headers: getAuthorizationHeaders(),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  return await resp.json();
}

async function fetchParseEndpoint<T>(jobId: string, suffix: string): Promise<T> {
  const resp = await fetch(apiPath(`/parse/analysis/${jobId}${suffix}`));
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  const body = await resp.json();
  return body.data as T;
}

export async function fetchParseDetails(jobId: string): Promise<ParseDetails> {
  const [readme, tree, stack, codemap, summary] = await Promise.all([
    fetchParseEndpoint<ParseReadmeData>(jobId, "/readme"),
    fetchParseEndpoint<ParseTreeData>(jobId, "/tree"),
    fetchParseEndpoint<ParseStackData>(jobId, "/stack"),
    fetchParseEndpoint<ParseCodeMapData>(jobId, "/codemap"),
    fetchParseEndpoint<ParseSummaryData>(jobId, "/summary"),
  ]);

  return { readme, tree, stack, codemap, summary };
}

export async function fetchAnalysisHistory(
  page = 1,
  limit = 30,
  scope: "private" | "team" | "all" = "all",
  teamId?: string | null,
): Promise<AnalysisHistoryResponse> {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
    scope,
  });
  if (teamId) params.set("teamId", teamId);
  const resp = await fetch(apiPath(`/list/analysis?${params.toString()}`), {
    headers: {
      ...getAuthorizationHeaders(),
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
    throw await parseApiError(resp);
  }

  return await resp.json();
}

/**
 * EventSource/WebSocket은 Authorization 헤더를 보낼 수 없으므로,
 * private/team 분석의 실시간 채널 접근을 위해 토큰을 query param으로 전달한다.
 */
function withToken(url: string): string {
  const token = getAccessToken();
  if (!token) return url;
  return `${url}${url.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`;
}

/**
 * GET /api/repo/analysis/{jobId}/events — SSE 이벤트 스트림
 * Returns EventSource URL for SSE streaming
 */
export function buildSseUrl(jobId: string): string {
  return withToken(apiPath(`/repo/analysis/${jobId}/events`));
}

/**
 * Build WebSocket URL for real-time progress
 * WS /ws/list/progress/{jobId}
 */
export function buildWsUrl(wsPath: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const path = wsPath.startsWith("/") ? wsPath : `/${wsPath}`;
  const base = /^wss?:\/\//i.test(wsPath) ? wsPath : `${proto}//${host}${BASE_PATH}${path}`;
  return withToken(base);
}

/**
 * GET /api/repo/analysis/{jobId}/files/content — job 기준 파일 컨텐츠 조회
 */
export async function fetchFileContent(
  jobId: string,
  path: string,
  signal?: AbortSignal,
): Promise<{
  data: {
    path: string;
    content: string;
    language: string | null;
    lines: number;
    truncated: boolean;
  };
}> {
  const resp = await fetch(
    apiPath(
      `/repo/analysis/${encodeURIComponent(jobId)}/files/content?path=${encodeURIComponent(path)}`,
    ),
    { headers: getAuthorizationHeaders(), signal },
  );

  if (!resp.ok) {
    throw await parseApiError(resp);
  }

  return await resp.json();
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
      ...getAuthorizationHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    throw await parseApiError(resp);
  }

  return await resp.json();
}

/**
 * DELETE /api/list/analysis/{jobId} — 분석 작업 삭제
 */
export async function deleteAnalysisJob(jobId: string): Promise<void> {
  const resp = await fetch(apiPath(`/list/analysis/${jobId}`), {
    method: "DELETE",
    headers: {
      ...getAuthorizationHeaders(),
    },
  });

  if (!resp.ok) {
    throw await parseApiError(resp);
  }
}

export async function fetchTeams(): Promise<TeamWorkspace[]> {
  const resp = await fetch(apiPath("/teams"), {
    headers: getAuthorizationHeaders(),
  });
  if (resp.status === 401 || resp.status === 404) return [];
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  const payload = await resp.json();
  return (payload.teams || payload.data?.teams || []) as TeamWorkspace[];
}

export async function createTeam(name: string): Promise<TeamWorkspace> {
  const resp = await fetch(apiPath("/teams"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthorizationHeaders(),
    },
    body: JSON.stringify({ name }),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  return await resp.json();
}

export async function inviteTeamMember(teamId: string, email: string): Promise<void> {
  const resp = await fetch(apiPath(`/teams/${teamId}/invites`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthorizationHeaders(),
    },
    body: JSON.stringify({ email }),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
}

export async function fetchMyInvites(): Promise<TeamInviteItem[]> {
  const resp = await fetch(apiPath("/team-invites"), {
    headers: getAuthorizationHeaders(),
  });
  if (resp.status === 401 || resp.status === 404) return [];
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  const payload = await resp.json();
  return (payload.invites || payload.data?.invites || []) as TeamInviteItem[];
}

export async function acceptInvite(inviteId: string): Promise<void> {
  const resp = await fetch(apiPath(`/team-invites/${inviteId}/accept`), {
    method: "POST",
    headers: getAuthorizationHeaders(),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
}

export async function declineInvite(inviteId: string): Promise<void> {
  const resp = await fetch(apiPath(`/team-invites/${inviteId}/decline`), {
    method: "POST",
    headers: getAuthorizationHeaders(),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
}

export async function removeTeamMember(teamId: string, userId: string): Promise<void> {
  const resp = await fetch(apiPath(`/teams/${teamId}/members/${userId}`), {
    method: "DELETE",
    headers: getAuthorizationHeaders(),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
}

export async function leaveTeam(teamId: string): Promise<void> {
  const resp = await fetch(apiPath(`/teams/${teamId}/leave`), {
    method: "POST",
    headers: getAuthorizationHeaders(),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
}

export async function fetchTeamInvites(teamId: string): Promise<TeamInviteItem[]> {
  const resp = await fetch(apiPath(`/teams/${teamId}/invites`), {
    headers: getAuthorizationHeaders(),
  });
  if (resp.status === 401 || resp.status === 404) return [];
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  const payload = await resp.json();
  return (payload.invites || payload.data?.invites || []) as TeamInviteItem[];
}

export async function cancelTeamInvite(teamId: string, inviteId: string): Promise<void> {
  const resp = await fetch(apiPath(`/teams/${teamId}/invites/${inviteId}/cancel`), {
    method: "POST",
    headers: getAuthorizationHeaders(),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
}

export async function fetchTeamMembers(teamId: string): Promise<import("@/common/types/contracts").TeamMemberResponse[]> {
  const resp = await fetch(apiPath(`/teams/${teamId}/members`), {
    headers: getAuthorizationHeaders(),
  });
  if (resp.status === 401 || resp.status === 404) return [];
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  return await resp.json();
}
