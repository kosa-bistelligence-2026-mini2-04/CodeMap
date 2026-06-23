/**
 * PROJECT-AUTH-F-103: 인증 상태 전역 관리 (Zustand)
 *
 * useAuthStore: { user, accessToken, isLoggedIn, login(), logout(), restoreSession() }
 * 페이지 새로고침 시 localStorage → store 자동 복원.
 */

"use client";

import { create } from "zustand";
import {
  login as apiLogin,
  logout as apiLogout,
  refreshAccessToken,
  type LoginRequest,
} from "@/features/auth/api/authApi";

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

  /** 로그인: API 호출 + 토큰 저장 + store 업데이트 */
  login: (payload: LoginRequest) => Promise<void>;

  /** 로그아웃: API 호출 + 토큰 제거 + store 초기화 */
  logout: () => Promise<void>;

  /** 페이지 새로고침 시 localStorage → store 복원 */
  restoreSession: () => void;

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

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  isLoggedIn: false,

  // ──────────────────────────────────────────────
  // 로그인
  // ──────────────────────────────────────────────
  login: async (payload: LoginRequest) => {
    const resp = await apiLogin(payload); // 토큰은 authApi에서 localStorage에 저장
    const { accessToken } = resp.data;

    const jwtPayload = parseJwtPayload(accessToken);
    const user: AuthUser | null = jwtPayload?.sub && jwtPayload?.email
      ? { userId: jwtPayload.sub, email: jwtPayload.email }
      : null;

    set({ accessToken, user, isLoggedIn: true });
  },

  // ──────────────────────────────────────────────
  // 로그아웃
  // ──────────────────────────────────────────────
  logout: async () => {
    await apiLogout(); // localStorage 토큰 제거 포함
    set({ user: null, accessToken: null, isLoggedIn: false });
  },

  // ──────────────────────────────────────────────
  // 세션 복원 (새로고침 시 _app 또는 layout에서 호출)
  // ──────────────────────────────────────────────
  restoreSession: () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("cm-access-token");
    if (!token) return;

    const jwtPayload = parseJwtPayload(token);
    if (!jwtPayload?.sub || !jwtPayload?.email) return;

    // 만료 시간 확인
    const payload = jwtPayload as { sub: string; email: string; exp?: number };
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      // 만료 → refresh 시도
      get().refreshToken();
      return;
    }

    set({
      accessToken: token,
      user: { userId: payload.sub, email: payload.email },
      isLoggedIn: true,
    });
  },

  // ──────────────────────────────────────────────
  // Access Token 갱신
  // ──────────────────────────────────────────────
  refreshToken: async () => {
    const newToken = await refreshAccessToken();
    if (!newToken) {
      set({ user: null, accessToken: null, isLoggedIn: false });
      return null;
    }

    const jwtPayload = parseJwtPayload(newToken);
    const user: AuthUser | null =
      jwtPayload?.sub && jwtPayload?.email
        ? { userId: jwtPayload.sub as string, email: jwtPayload.email as string }
        : null;

    set({ accessToken: newToken, user, isLoggedIn: true });
    return newToken;
  },
}));
