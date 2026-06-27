"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { translations, type Locale } from "@/common/i18n/translations";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type Theme = "dark" | "light";

interface AppContextValue {
  theme: Theme;
  locale: Locale;
  t: (typeof translations)[Locale];
  toggleTheme: () => void;
  toggleLocale: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Context
// ─────────────────────────────────────────────────────────────────────────────

const AppContext = createContext<AppContextValue | null>(null);

// ─────────────────────────────────────────────────────────────────────────────
// Provider
// ─────────────────────────────────────────────────────────────────────────────

export function AppProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark");
  const [locale, setLocale] = useState<Locale>("en");
  const [mounted, setMounted] = useState(false);

  // Hydrate from localStorage after mount (avoids SSR mismatch)
  useEffect(() => {
    queueMicrotask(async () => {
      const savedTheme = (localStorage.getItem("cm-theme") as Theme) ?? "dark";
      const savedLocale = (localStorage.getItem("cm-locale") as Locale) ?? "en";
      setTheme(savedTheme);
      setLocale(savedLocale);

      // Restore Auth Session
      const { useAuthStore } = await import("@/features/auth/store/useAuthStore");
      useAuthStore.getState().restoreSession();

      setMounted(true);
    });
  }, []);

  // Apply theme class to <html>
  useEffect(() => {
    if (!mounted) return;
    const root = document.documentElement;
    root.setAttribute("data-theme", theme);
    localStorage.setItem("cm-theme", theme);
  }, [theme, mounted]);

  // Persist locale and update HTML lang
  useEffect(() => {
    if (!mounted) return;
    document.documentElement.lang = locale;
    localStorage.setItem("cm-locale", locale);
  }, [locale, mounted]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const toggleLocale = useCallback(() => {
    setLocale((prev) => (prev === "en" ? "ko" : "en"));
  }, []);

  const t = translations[locale];

  return (
    <AppContext.Provider value={{ theme, locale, t, toggleTheme, toggleLocale }}>
      {children}
    </AppContext.Provider>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────────────────────────────────────

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useApp must be used inside <AppProvider>");
  }
  return ctx;
}
