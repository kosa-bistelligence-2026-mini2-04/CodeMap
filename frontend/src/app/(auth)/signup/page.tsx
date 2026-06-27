"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useApp } from "@/common/contexts/AppContext";
import { useAuthStore } from "@/features/auth/store/useAuthStore";
import { register } from "@/features/auth/api/authApi";
import { ApiError } from "@/common/api/error";
import { AlertTriangle, Mail, Lock, ArrowRight, Loader2, CheckCircle2 } from "lucide-react";

export default function SignUpPage() {
  const router = useRouter();
  const { theme, t } = useApp();
  const isDark = theme === "dark";
  const login = useAuthStore((state) => state.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  // Validation status
  const isPasswordLongEnough = password.length >= 8;
  const doPasswordsMatch = password === confirmPassword && password.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!doPasswordsMatch) {
      setError(t.auth.signup.passwordMismatch);
      return;
    }
    if (!isPasswordLongEnough) {
      setError(t.auth.signup.passwordTooShort);
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
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        const localizedMsg = t.auth.errors[err.code as keyof typeof t.auth.errors];
        setError(localizedMsg || err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t.auth.errors.default);
      }
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
            {t.auth.signUpSuccessTitle}
          </h2>
          <p className={`text-sm ${isDark ? "text-zinc-400" : "text-zinc-500"}`}>
            {t.auth.signUpSuccessDesc}
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
          {t.nav.signUp}
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
              {t.auth.emailLabel}
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
                placeholder={t.auth.emailPlaceholder}
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
              {t.auth.passwordLabel}
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
                placeholder={t.auth.passwordMinPlaceholder}
              />
            </div>
            {password.length > 0 && (
              <p className={`mt-1.5 text-[10px] flex items-center gap-1 ${isPasswordLongEnough ? "text-emerald-500" : "text-amber-500"}`}>
                {isPasswordLongEnough ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                {isPasswordLongEnough ? t.auth.signup.passwordLengthOk : t.auth.signup.passwordTooShort}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="confirmPassword"
              className={`block text-xs font-medium mb-1.5 ${
                isDark ? "text-zinc-400" : "text-zinc-600"
              }`}
            >
              {t.auth.confirmPasswordLabel}
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
                placeholder={t.auth.passwordPlaceholder}
              />
            </div>
            {confirmPassword.length > 0 && (
              <p className={`mt-1.5 text-[10px] flex items-center gap-1 ${doPasswordsMatch ? "text-emerald-500" : "text-red-500"}`}>
                {doPasswordsMatch ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                {doPasswordsMatch ? t.auth.signup.passwordMatchOk : t.auth.signup.passwordMismatch}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading || !email || !password || !confirmPassword || !isPasswordLongEnough || !doPasswordsMatch}
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
                {t.auth.signUpBtn} <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <p
          className={`mt-6 text-center text-xs ${
            isDark ? "text-zinc-400" : "text-zinc-500"
          }`}
        >
          {t.auth.haveAccount}{" "}
          <Link
            href="/signin"
            className={`font-semibold hover:underline ${
              isDark ? "text-white" : "text-zinc-900"
            }`}
          >
            {t.nav.signIn}
          </Link>
        </p>
      </div>
    </div>
  );
}
