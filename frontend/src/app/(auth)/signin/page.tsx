"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useApp } from "@/common/contexts/AppContext";
import { useAuthStore } from "@/features/auth/store/useAuthStore";
import { ApiError } from "@/common/api/error";
import { AlertTriangle, Mail, Lock, ArrowRight, Loader2 } from "lucide-react";

export default function SignInPage() {
  const router = useRouter();
  const { theme, t } = useApp();
  const isDark = theme === "dark";
  const login = useAuthStore((state) => state.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login({ email, password });
      router.push("/analyze"); // 로그인 성공 시 프로젝트 분석 페이지로
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        const localizedMsg = t.auth.errors[err.code as keyof typeof t.auth.errors];
        setError(localizedMsg || err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t.auth.errors.default);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const inputClass = `w-full pl-10 pr-4 py-2.5 rounded-lg border bg-transparent text-sm transition-all outline-none focus:ring-2 ${
    isDark
      ? "border-zinc-700 focus:border-zinc-500 focus:ring-zinc-500/20 text-white placeholder-zinc-500"
      : "border-zinc-300 focus:border-zinc-400 focus:ring-zinc-400/20 text-black placeholder-zinc-400"
  }`;

  const iconClass = `absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${
    isDark ? "text-zinc-500" : "text-zinc-400"
  }`;

  return (
    <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-[400px]">
      <div
        className={`px-6 py-8 sm:rounded-2xl sm:px-10 border backdrop-blur-md shadow-xl ${
          isDark
            ? "bg-zinc-900/60 border-zinc-800 shadow-black/40"
            : "bg-white/80 border-zinc-200 shadow-zinc-200/50"
        }`}
      >
        <h2
          className={`text-center text-xl font-bold mb-6 ${
            isDark ? "text-white" : "text-zinc-900"
          }`}
        >
          계정에 로그인하세요
        </h2>

        {error && (
          <div
            className={`mb-6 flex items-start gap-3 p-3 rounded-lg border text-sm ${
              isDark
                ? "bg-red-500/10 border-red-500/20 text-red-400"
                : "bg-red-50 border-red-200 text-red-600"
            }`}
          >
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <p>{error}</p>
          </div>
        )}

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label
              htmlFor="email"
              className={`block text-xs font-medium mb-1.5 ${
                isDark ? "text-zinc-400" : "text-zinc-600"
              }`}
            >
              이메일 주소
            </label>
            <div className="relative">
              <Mail className={iconClass} />
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
                placeholder="you@example.com"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="password"
              className={`block text-xs font-medium mb-1.5 ${
                isDark ? "text-zinc-400" : "text-zinc-600"
              }`}
            >
              비밀번호
            </label>
            <div className="relative">
              <Lock className={iconClass} />
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading || !email || !password}
            className={`w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold transition-all ${
              isDark
                ? "bg-white text-black hover:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-500"
                : "bg-zinc-900 text-white hover:bg-zinc-800 disabled:bg-zinc-200 disabled:text-zinc-400"
            }`}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                로그인 <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <p
          className={`mt-8 text-center text-xs ${
            isDark ? "text-zinc-400" : "text-zinc-500"
          }`}
        >
          {"계정이 없으신가요?"}{" "}
          <Link
            href="/signup"
            className={`font-semibold hover:underline ${
              isDark ? "text-white" : "text-zinc-900"
            }`}
          >
            회원가입
          </Link>
        </p>
      </div>
    </div>
  );
}
