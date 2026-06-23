/**
 * PROJECT-AUTH-F-101: Auth API 클라이언트 함수
 *
 * 로그인/회원가입/토큰 갱신/로그아웃 API 호출 함수 모음.
 * 토큰 저장 키는 "cm-access-token" / "cm-refresh-token" 으로 통일.
 */

const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");
const BASE_URL = `${BASE_PATH}/api/auth`;

// ── 타입 정의 ────────────────────────────────────────────────────────────────

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface RegisterResponse {
  code: number;
  message: string;
  data: {
    userId: string;
    email: string;
  };
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  code: number;
  message: string;
  data: {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
  };
}

export interface RefreshResponse {
  code: number;
  message: string;
  data: {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
  };
}

export interface LogoutResponse {
  code: number;
  message: string;
  data: null;
}

// ── 공통 헬퍼 ───────────────────────────────────────────────────────────────

function getStoredRefreshToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("cm-refresh-token") || "";
}

function saveTokens(accessToken: string, refreshToken?: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem("cm-access-token", accessToken);
  if (refreshToken) {
    localStorage.setItem("cm-refresh-token", refreshToken);
  }
}

function clearTokens() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("cm-access-token");
  localStorage.removeItem("cm-refresh-token");
}

// ── API 함수 ─────────────────────────────────────────────────────────────────

/**
 * 회원가입 (AUTH-API-001)
 * POST /api/auth/register
 */
export async function register(payload: RegisterRequest): Promise<RegisterResponse> {
  const resp = await fetch(`${BASE_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err?.error?.message || `회원가입 실패 (HTTP ${resp.status})`);
  }
  return resp.json();
}

/**
 * 로그인 (AUTH-API-002)
 * POST /api/auth/login
 * 성공 시 토큰을 localStorage에 자동 저장.
 */
export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const resp = await fetch(`${BASE_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err?.error?.message || `로그인 실패 (HTTP ${resp.status})`);
  }
  const data: LoginResponse = await resp.json();
  saveTokens(data.data.accessToken, data.data.refreshToken);
  return data;
}

/**
 * 토큰 갱신 (AUTH-API-003)
 * POST /api/auth/refresh
 * localStorage의 cm-refresh-token을 사용하여 새 accessToken 발급.
 */
export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;

  try {
    const resp = await fetch(`${BASE_URL}/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken }),
    });
    if (!resp.ok) {
      clearTokens();
      return null;
    }
    const data: RefreshResponse = await resp.json();
    saveTokens(data.data.accessToken, data.data.refreshToken);
    return data.data.accessToken;
  } catch {
    clearTokens();
    return null;
  }
}

/**
 * 로그아웃 (AUTH-API-004)
 * POST /api/auth/logout
 * 서버 측 Refresh Token 무효화 후 localStorage 초기화.
 */
export async function logout(): Promise<void> {
  const accessToken = typeof window !== "undefined"
    ? localStorage.getItem("cm-access-token") || ""
    : "";
  const refreshToken = getStoredRefreshToken();

  try {
    await fetch(`${BASE_URL}/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ refreshToken }),
    });
  } finally {
    // 서버 응답 실패해도 로컬 토큰은 반드시 제거
    clearTokens();
  }
}
