"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useApp } from "@/common/contexts/AppContext";
import { useAuthStore } from "@/features/auth/store/useAuthStore";
import { register } from "@/features/auth/api/authApi";
import { AlertTriangle, Mail, Lock, ArrowRight, Loader2, CheckCircle2 } from "lucide-react";

export default function SignUpPage() {
  const router = useRouter();
  const { theme } = useApp();
  const isDark = theme === "dark";
  const login = useAuthStore((state) => state.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setIsLoading(true);

    try {
      // 1. 회원가입 API 호출
      await register({ email, password });

      // 2. 가입 성공 시 자동 로그인 시도
      await login({ email, password });

      // 3. 성공 상태 표시 후 이동
      setIsSuccess(true);
      setTimeout(() => {
        router.push("/analyze");
      }, 1000);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Failed to create an account. Please try again.";
      setError(errorMsg);
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

  if (isSuccess) {
    return (
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-[400px]">
        <div
          className={`px-6 py-12 sm:rounded-2xl text-center border backdrop-blur-md shadow-xl ${
            isDark
              ? "bg-zinc-900/60 border-zinc-800 shadow-black/40"
              : "bg-white/80 border-zinc-200 shadow-zinc-200/50"
          }`}
        >
          <CheckCircle2 className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
          <h2 className={`text-xl font-bold mb-2 ${isDark ? "text-white" : "text-black"}`}>
            Welcome to CodeMap AI!
          </h2>
          <p className={`text-sm ${isDark ? "text-zinc-400" : "text-zinc-500"}`}>
            Your account has been created. Redirecting...
          </p>
        </div>
      </div>
    );
  }

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
          Create your account
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

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label
              htmlFor="email"
              className={`block text-xs font-medium mb-1.5 ${
                isDark ? "text-zinc-400" : "text-zinc-600"
              }`}
            >
              Email address
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
              Password
            </label>
            <div className="relative">
              <Lock className={iconClass} />
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
                placeholder="At least 8 characters"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="confirmPassword"
              className={`block text-xs font-medium mb-1.5 ${
                isDark ? "text-zinc-400" : "text-zinc-600"
              }`}
            >
              Confirm Password
            </label>
            <div className="relative">
              <Lock className={iconClass} />
              <input
                id="confirmPassword"
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={inputClass}
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading || !email || !password || !confirmPassword}
            className={`w-full mt-2 flex justify-center items-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold transition-all ${
              isDark
                ? "bg-white text-black hover:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-500"
                : "bg-zinc-900 text-white hover:bg-zinc-800 disabled:bg-zinc-200 disabled:text-zinc-400"
            }`}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                Sign up <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <p
          className={`mt-6 text-center text-xs ${
            isDark ? "text-zinc-400" : "text-zinc-500"
          }`}
        >
          Already have an account?{" "}
          <Link
            href="/signin"
            className={`font-semibold hover:underline ${
              isDark ? "text-white" : "text-zinc-900"
            }`}
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
