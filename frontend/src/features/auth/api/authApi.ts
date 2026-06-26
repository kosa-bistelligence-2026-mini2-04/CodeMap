/**
 * PROJECT-AUTH-F-101: Auth API 클라이언트 함수
 *
 * 로그인/회원가입/토큰 갱신/로그아웃 API 호출 함수 모음.
 * refresh token은 httpOnly 쿠키로 관리하고, access token만 호출자 메모리에 보관합니다.
 */

const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");
const BASE_URL = `${BASE_PATH}/api/auth`;

// ── 타입 정의 ────────────────────────────────────────────────────────────────

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface RegisterResponse {
  success: boolean;
  code: number;
  message: string;
  error_code?: string;
  data: {
    userId: string;
    email: string;
  } | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  code: number;
  message: string;
  error_code?: string;
  data: {
    accessToken: string;
    expiresIn: number;
  } | null;
}

export interface RefreshResponse {
  success: boolean;
  code: number;
  message: string;
  data: {
    accessToken: string;
    expiresIn: number;
  } | null;
}

export interface LogoutResponse {
  success: boolean;
  code: number;
  message: string;
  data: null;
}

// ── 공통 헬퍼 ───────────────────────────────────────────────────────────────

// ── API 함수 ─────────────────────────────────────────────────────────────────

import { parseApiError, ApiError } from "@/common/api/error";

/**
 * 회원가입 (AUTH-API-001)
 * POST /api/auth/register
 */
export async function register(payload: RegisterRequest): Promise<RegisterResponse> {
  const resp = await fetch(`${BASE_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  const data: RegisterResponse = await resp.json();
  if (!data.success) {
    throw new ApiError(200, {
      code: data.code,
      message: data.message || `회원가입 실패`,
      error: data.error_code ? { code: data.error_code } : undefined,
    });
  }
  return data;
}

/**
 * 로그인 (AUTH-API-002)
 * POST /api/auth/login
 * 성공 시 refresh token은 httpOnly 쿠키로 설정되고 access token만 응답으로 받습니다.
 */
export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const resp = await fetch(`${BASE_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw await parseApiError(resp);
  }
  const data: LoginResponse = await resp.json();
  if (!data.success) {
    throw new ApiError(200, {
      code: data.code,
      message: data.message || `로그인 실패`,
      error: data.error_code ? { code: data.error_code } : undefined,
    });
  }
  return data;
}

/**
 * 토큰 갱신 (AUTH-API-003)
 * POST /api/auth/refresh
 * httpOnly refresh cookie를 사용하여 새 accessToken 발급.
 */
export async function refreshAccessToken(): Promise<string | null> {
  try {
    const resp = await fetch(`${BASE_URL}/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    });
    if (!resp.ok) {
      return null;
    }
    const data: RefreshResponse = await resp.json();
    if (!data.success || !data.data) {
      return null;
    }
    return data.data.accessToken;
  } catch {
    return null;
  }
}

/**
 * 로그아웃 (AUTH-API-004)
 * POST /api/auth/logout
 * 서버 측 Refresh Token 무효화 후 httpOnly 쿠키 삭제.
 */
export async function logout(accessToken?: string | null): Promise<void> {
  try {
    await fetch(`${BASE_URL}/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      credentials: "include",
    });
  } catch {
    // 클라이언트 상태 정리는 store에서 항상 수행합니다.
  }
}
