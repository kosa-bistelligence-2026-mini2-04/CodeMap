"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Sun, Moon, LogOut } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";
import { useAuthStore } from "@/features/auth/store/useAuthStore";

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const isHome = pathname === "/";
  const { theme, locale, toggleTheme, toggleLocale, t } = useApp();
  const user = useAuthStore((state) => state.user);
  const isLoggedIn = useAuthStore((state) => state.isLoggedIn);
  const logout = useAuthStore((state) => state.logout);

  const isDark = theme === "dark";

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  // Toggle button style — adapts to current theme
  const toggleBtnClass =
    "flex items-center justify-center w-8 h-8 rounded-lg border transition-all duration-200 cursor-pointer hover:scale-105 active:scale-95 " +
    (isDark
      ? "border-zinc-700 bg-zinc-900/60 text-zinc-400 hover:border-zinc-500 hover:text-white"
      : "border-zinc-300 bg-white/80 text-zinc-500 hover:border-zinc-400 hover:text-zinc-900");

  const navbarBase = isDark
    ? "border-zinc-800/80 bg-zinc-950/90"
    : "border-zinc-200/80 bg-white/90";

  const textBase = isDark ? "text-white" : "text-zinc-900";
  const subText = isDark ? "text-zinc-400" : "text-zinc-500";
  const linkHover = isDark
    ? "text-zinc-400 hover:text-white"
    : "text-zinc-500 hover:text-zinc-900";

  // Home page renders its own fixed top-right buttons — Navbar hidden
  if (isHome) {
    return (
      // Fixed top-right toggles that appear on home page
      <div className="fixed top-4 right-4 md:top-5 md:right-5 z-[100] flex items-center gap-2">
        {/* Language Toggle */}
        <button
          onClick={toggleLocale}
          className={toggleBtnClass}
          title={locale === "en" ? "한국어로 전환" : "Switch to English"}
          aria-label="Toggle language"
        >
          <span className="text-[10px] font-bold leading-none">
            {locale === "en" ? "한" : "EN"}
          </span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className={toggleBtnClass}
          title={isDark ? "Light mode" : "Dark mode"}
          aria-label="Toggle theme"
        >
          {isDark ? (
            <Sun className="w-3.5 h-3.5" />
          ) : (
            <Moon className="w-3.5 h-3.5" />
          )}
        </button>

        {/* Launch App CTA / User Menu */}
        {isLoggedIn ? (
          <div className="flex items-center gap-2 ml-1">
            <span className={`text-xs font-semibold ${isDark ? "text-zinc-300" : "text-zinc-600"} hidden sm:inline-block`}>
              {user?.email?.split('@')[0]}
            </span>
            <button
              onClick={handleLogout}
              className={
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm " +
                (isDark
                  ? "bg-zinc-800 text-white hover:bg-zinc-700"
                  : "bg-zinc-100 text-black hover:bg-zinc-200")
              }
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <>
            <Link
              href="/signin"
              className={
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all " +
                (isDark ? "text-zinc-300 hover:text-white" : "text-zinc-600 hover:text-black")
              }
            >
              Sign in
            </Link>
            <Link
              href="/analyze"
              className={
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm " +
                (isDark
                  ? "bg-white text-black hover:bg-zinc-200"
                  : "bg-black text-white hover:bg-zinc-800")
              }
            >
              {t.nav.launchApp}
            </Link>
          </>
        )}
      </div>
    );
  }

  return (
    <header
      className={`sticky top-0 z-50 w-full border-b backdrop-blur-md transition-colors duration-300 ${navbarBase}`}
    >
      <div className="mx-auto max-w-7xl px-6 h-14 flex items-center justify-between">
        {/* Left: Logo + Nav links */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">

            <span className={`font-bold tracking-tight text-sm ${textBase}`}>
              CodeMap{" "}
              <span className={subText + " font-normal"}>AI</span>
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-5 text-xs font-semibold">
            <Link href="/" className={`${linkHover} transition-colors`}>
              {t.nav.home}
            </Link>
            <Link href="/analyze" className={`${pathname.startsWith("/analyze") || pathname.startsWith("/chat") ? textBase : linkHover} transition-colors`}>
              {locale === "ko" ? "프로젝트" : "Projects"}
            </Link>
          </nav>
        </div>

        {/* Right: Toggles + CTA */}
        <div className="flex items-center gap-2">
          {/* Language Toggle */}
          <button
            onClick={toggleLocale}
            className={toggleBtnClass}
            title={locale === "en" ? "한국어로 전환" : "Switch to English"}
            aria-label="Toggle language"
          >
            <span className="text-[10px] font-bold leading-none">
              {locale === "en" ? "한" : "EN"}
            </span>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className={toggleBtnClass}
            title={isDark ? "Light mode" : "Dark mode"}
            aria-label="Toggle theme"
          >
            {isDark ? (
              <Sun className="w-3.5 h-3.5" />
            ) : (
              <Moon className="w-3.5 h-3.5" />
            )}
          </button>

          {/* Project repository */}
          <a
            href="https://github.com/kosa-bistelligence-2026-mini2-04/CodeMap"
            target="_blank"
            rel="noopener noreferrer"
            className={`text-xs font-semibold ${linkHover} transition-colors ml-1 hidden sm:inline-block`}
          >
            {t.nav.github}
          </a>

          {/* User Section */}
          <div className="flex items-center gap-2 ml-2 pl-2 border-l border-zinc-200 dark:border-zinc-800">
            {isLoggedIn ? (
            <button
              onClick={handleLogout}
              className={
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all " +
                (isDark
                  ? "bg-zinc-800/80 text-zinc-300 hover:bg-zinc-700 hover:text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 hover:text-black")
              }
              title="Sign out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline-block">Sign out</span>
            </button>
            ) : (
              <>
                <Link
                  href="/signin"
                  className={`text-xs font-bold transition-all px-2 py-1.5 ${
                    isDark ? "text-zinc-300 hover:text-white" : "text-zinc-600 hover:text-black"
                  }`}
                >
                  Sign in
                </Link>
                <Link
                  href="/signup"
                  className={
                    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm " +
                    (isDark
                      ? "bg-white text-black hover:bg-zinc-200"
                      : "bg-black text-white hover:bg-zinc-800")
                  }
                >
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
