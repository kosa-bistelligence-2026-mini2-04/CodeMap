"use client";

import { useApp } from "@/common/contexts/AppContext";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { theme } = useApp();
  const isDark = theme === "dark";

  return (
    <div
      className={`min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden ${
        isDark ? "bg-zinc-950" : "bg-zinc-50"
      }`}
    >
      {/* Background decorations */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        <div
          className={`absolute -top-1/4 -right-1/4 w-[800px] h-[800px] rounded-full blur-[120px] opacity-30 ${
            isDark ? "bg-indigo-900/40" : "bg-indigo-200/50"
          }`}
        />
        <div
          className={`absolute -bottom-1/4 -left-1/4 w-[600px] h-[600px] rounded-full blur-[100px] opacity-30 ${
            isDark ? "bg-emerald-900/20" : "bg-emerald-200/40"
          }`}
        />
      </div>

      <div className="relative z-10 sm:mx-auto sm:w-full sm:max-w-md">
        <Link
          href="/"
          className={`absolute -top-12 left-0 flex items-center gap-1 text-sm font-medium transition-colors ${
            isDark ? "text-zinc-400 hover:text-white" : "text-zinc-500 hover:text-black"
          }`}
        >
          <ChevronLeft className="w-4 h-4" />
          Home
        </Link>
        <div className="flex justify-center text-center">
          <Link href="/" className="inline-block">
            <span
              className={`text-2xl font-bold tracking-tight ${
                isDark ? "text-white" : "text-black"
              }`}
            >
              CodeMap <span className="font-normal text-zinc-500">AI</span>
            </span>
          </Link>
        </div>
        {children}
      </div>
    </div>
  );
}
