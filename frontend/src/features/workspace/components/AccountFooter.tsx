"use client";

import { useRouter } from "next/navigation";
import { LogOut, LogIn, User } from "lucide-react";
import { useAuthStore } from "@/features/auth/store/useAuthStore";

interface AccountFooterProps {
  isDark: boolean;
  isKo: boolean;
}

// ──────────────────────────────────────────────
// 사이드바 하단 계정 영역 (로그인 이메일 / 로그아웃)
// ──────────────────────────────────────────────
export function AccountFooter({ isDark, isKo }: AccountFooterProps) {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const isLoggedIn = useAuthStore((state) => state.isLoggedIn);
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    router.push("/signin");
  };

  return (
    <div className={`shrink-0 border-t p-3 ${isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-white"}`}>
      {isLoggedIn && user ? (
        <div className="flex items-center gap-2">
          <div className={`flex size-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${isDark ? "bg-zinc-800 text-zinc-200" : "bg-zinc-100 text-zinc-700"}`}>
            {user.email?.[0]?.toUpperCase() || <User className="size-3.5" />}
          </div>
          <span className={`min-w-0 flex-1 truncate text-[11px] font-medium ${isDark ? "text-zinc-300" : "text-zinc-700"}`} title={user.email}>
            {user.email}
          </span>
          <button
            type="button"
            onClick={handleLogout}
            title={isKo ? "로그아웃" : "Log out"}
            className={`shrink-0 rounded-md p-1.5 transition ${isDark ? "text-zinc-500 hover:bg-zinc-800 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-900"}`}
          >
            <LogOut className="size-3.5" />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => router.push("/signin")}
          className={`flex w-full items-center justify-center gap-1.5 rounded-lg border px-2.5 py-2 text-[11px] font-semibold transition ${isDark ? "border-zinc-800 text-zinc-300 hover:bg-zinc-900" : "border-zinc-200 text-zinc-700 hover:bg-zinc-50"}`}
        >
          <LogIn className="size-3.5" /> {isKo ? "로그인" : "Sign in"}
        </button>
      )}
    </div>
  );
}
