/**
 * PROJECT-AUTH-F-103: 인증 상태 전역 관리 (Zustand)
 *
 * useAuthStore: { user, accessToken, isLoggedIn, login(), logout(), restoreSession() }
 * 페이지 새로고침 시 httpOnly refresh cookie → access token 재발급으로 복원.
 */

"use client";

import { create } from "zustand";
import {
  login as apiLogin,
  logout as apiLogout,
  refreshAccessToken,
  type LoginRequest,
} from "@/features/auth/api/authApi";
import { setAccessToken } from "@/features/auth/utils/tokenMemory";

// ── 타입 ─────────────────────────────────────────────────────────────────────

export interface AuthUser {
  /** JWT sub (user UUID) */
  userId: string;
  email: string;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  isLoggedIn: boolean;
  isRestoring: boolean;

  /** 로그인: API 호출 + 토큰 저장 + store 업데이트 */
  login: (payload: LoginRequest) => Promise<void>;

  /** 로그아웃: API 호출 + 토큰 제거 + store 초기화 */
  logout: () => Promise<void>;

  /** 페이지 새로고침 시 refresh cookie → store 복원 */
  restoreSession: () => Promise<void>;

  /** Access Token 만료 시 갱신 (fetch interceptor에서 호출) */
  refreshToken: () => Promise<string | null>;
}

// ── JWT payload 파싱 (디코딩만, 검증은 서버에서) ─────────────────────────────

function parseJwtPayload(token: string): { sub?: string; email?: string } | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

// ── Zustand Store ─────────────────────────────────────────────────────────────

let refreshPromise: Promise<string | null> | null = null;

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  isLoggedIn: false,
  isRestoring: true,

  // ──────────────────────────────────────────────
  // 로그인
  // ──────────────────────────────────────────────
  login: async (payload: LoginRequest) => {
    const resp = await apiLogin(payload);
    if (!resp.data) {
      throw new Error("서버 응답에 인증 토큰이 포함되어 있지 않습니다.");
    }
    const { accessToken } = resp.data;

    const jwtPayload = parseJwtPayload(accessToken);
    const user: AuthUser | null = jwtPayload?.sub && jwtPayload?.email
      ? { userId: jwtPayload.sub, email: jwtPayload.email }
      : null;

    setAccessToken(accessToken);
    set({ accessToken, user, isLoggedIn: true });
  },

  // ──────────────────────────────────────────────
  // 로그아웃
  // ──────────────────────────────────────────────
  logout: async () => {
    await apiLogout(get().accessToken);
    setAccessToken(null);
    set({ user: null, accessToken: null, isLoggedIn: false });
  },

  // ──────────────────────────────────────────────
  // 세션 복원 (새로고침 시 _app 또는 layout에서 호출)
  // ──────────────────────────────────────────────
  restoreSession: async () => {
    if (typeof window === "undefined") return;
    // 이미 로그인 상태라면 복원 스킵 및 isRestoring 해제
    if (get().isLoggedIn) {
      set({ isRestoring: false });
      return;
    }
    await get().refreshToken();
  },

  // ──────────────────────────────────────────────
  // Access Token 갱신
  // ──────────────────────────────────────────────
  refreshToken: async () => {
    // 1. 이미 유효한 토큰이 스토어에 세팅되어 있다면 Early Return
    if (get().accessToken && get().isLoggedIn) {
      set({ isRestoring: false });
      return get().accessToken;
    }

    // 2. 이미 활성화된 refresh API Promise가 존재한다면 재사용 (Promise Caching)
    if (refreshPromise) {
      return refreshPromise;
    }

    set({ isRestoring: true });

    refreshPromise = (async () => {
      try {
        const newToken = await refreshAccessToken();
        if (!newToken) {
          setAccessToken(null);
          set({ user: null, accessToken: null, isLoggedIn: false });
          return null;
        }

        const jwtPayload = parseJwtPayload(newToken);
        const user: AuthUser | null =
          jwtPayload?.sub && jwtPayload?.email
            ? { userId: jwtPayload.sub as string, email: jwtPayload.email as string }
            : null;

        setAccessToken(newToken);
        set({ accessToken: newToken, user, isLoggedIn: true });
        return newToken;
      } catch (err) {
        console.error("[useAuthStore] refreshToken failed:", err);
        setAccessToken(null);
        set({ user: null, accessToken: null, isLoggedIn: false });
        return null;
      } finally {
        refreshPromise = null;
        set({ isRestoring: false });
      }
    })();

    return refreshPromise;
  },
}));
