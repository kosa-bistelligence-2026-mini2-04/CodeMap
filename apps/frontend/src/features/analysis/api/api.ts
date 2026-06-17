import type {
  AnalyzeRequest,
  AnalyzeResponse,
  JobProgressResponse,
  ReportJsonResponse,
} from "@/common/types/contracts";

const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");
const BASE_URL = `${BASE_PATH}/api`;

export function apiPath(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${BASE_URL}${normalizedPath}`;
}

export async function startAnalysis(
  payload: AnalyzeRequest,
): Promise<AnalyzeResponse> {
  const resp = await fetch(apiPath("/analyze"), {
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
    throw new Error(errData?.error?.message || `Failed to start analysis: ${resp.status}`);
  }

  return await resp.json();
}

export async function fetchReportJson(
  jobId: string,
): Promise<ReportJsonResponse | JobProgressResponse> {
  const resp = await fetch(apiPath(`/report/${jobId}?format=json`));
  if (!resp.ok) {
    throw new Error(`Failed to fetch report JSON: ${resp.status}`);
  }
  return await resp.json();
}

export async function fetchReportHtml(jobId: string): Promise<string> {
  const resp = await fetch(apiPath(`/report/${jobId}?format=html`));
  if (!resp.ok) {
    throw new Error(`Failed to fetch report HTML: ${resp.status}`);
  }
  return await resp.text();
}

export function buildWsUrl(wsPath: string): string {
  if (/^wss?:\/\//i.test(wsPath)) return wsPath;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const path = wsPath.startsWith("/") ? wsPath : `/${wsPath}`;
  return `${proto}//${host}${BASE_PATH}${path}`;
}
