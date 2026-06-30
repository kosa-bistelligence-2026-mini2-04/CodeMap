"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/features/auth/store/useAuthStore";

const PUBLIC_ROUTES = ["/", "/signin", "/signup"];

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoggedIn, isRestoring } = useAuthStore();

  useEffect(() => {
    // 세션 복원 작업이 끝난 상태에서만 권한 검사 기동
    if (!isRestoring) {
      const isPublicRoute = PUBLIC_ROUTES.includes(pathname || "/");
      if (!isLoggedIn && !isPublicRoute) {
        // 비공개 라우트에 인증 없이 접근 시 로그인으로 리다이렉트
        router.replace("/signin");
      }
    }
  }, [isLoggedIn, isRestoring, pathname, router]);

  // 1. 세션 복원 중(Refresh Token 재발급 대기)일 때는 세련된 프리미엄 로딩 화면 노출
  if (isRestoring) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-zinc-950 text-zinc-100 select-none">
        {/* 미세 네온 블러 백그라운드 그라데이션 */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-purple-500/5 rounded-full blur-[150px] pointer-events-none" />

        <div className="flex flex-col items-center gap-6 z-10">
          {/* 부드러운 회전 애니메이션 스피너 */}
          <div className="relative size-12">
            <div className="absolute inset-0 rounded-full border-[3px] border-zinc-800" />
            <div className="absolute inset-0 rounded-full border-[3px] border-t-indigo-500 border-r-transparent border-b-transparent border-l-transparent animate-spin [animation-duration:0.8s]" />
          </div>
          <div className="flex flex-col items-center gap-1.5 text-center">
            <span className="text-sm font-semibold tracking-wider bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
              SECURE SESSION
            </span>
            <span className="text-[10px] tracking-widest text-zinc-500 uppercase">
              Verifying credentials
            </span>
          </div>
        </div>
      </div>
    );
  }

  // 2. 비로그인 유저가 비공개 라우트에 접근하여 리다이렉트 대기 상태일 때는 빈 화면을 유지해 Leakage 차단
  const isPublicRoute = PUBLIC_ROUTES.includes(pathname || "/");
  if (!isLoggedIn && !isPublicRoute) {
    return (
      <div className="fixed inset-0 z-50 bg-zinc-950" />
    );
  }

  // 3. 인증 완료 또는 공개 라우트는 정상 렌더링
  return <>{children}</>;
}
