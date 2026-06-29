/**
 * PROJECT-API-ERROR: 공통 API 에러 파서 및 인터페이스
 * ERROR_CODES.md 명세에 기반한 에러 처리
 */

import { setAccessToken } from "@/features/auth/utils/tokenMemory";

export interface StandardErrorResponse {
  code: number;
  message: string;
  data?: unknown;
  error?: {
    code: string;
    detail?: unknown;
    field?: string;
    retryable?: boolean;
  };
}

export class ApiError extends Error {
  public status: number;
  public code: string;
  public field?: string;
  public retryable: boolean;
  public detail: unknown;

  constructor(status: number, data: StandardErrorResponse) {
    const errCode = data.error?.code || data.code?.toString() || "UNKNOWN_ERROR";
    const errMsg = data.message || "서버 요청에 실패했습니다.";
    
    super(errMsg);
    this.name = "ApiError";
    this.status = status;
    this.code = errCode;
    this.field = data.error?.field;
    this.retryable = data.error?.retryable ?? false;
    this.detail = data.error?.detail;
  }
}

export async function parseApiError(response: Response): Promise<ApiError> {
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    data = { code: response.status, message: response.statusText || "Network Error" };
  }
  
  if (response.status === 401) {
    setAccessToken(null);
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }

  return new ApiError(response.status, data as StandardErrorResponse);
}
