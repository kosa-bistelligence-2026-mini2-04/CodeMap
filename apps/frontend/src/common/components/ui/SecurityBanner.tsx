"use client";

import { ShieldCheck, Cpu } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";

export function SecurityBanner() {
  const { theme, t } = useApp();
  const isDark = theme === "dark";

  return (
    <section className="w-full py-16 relative z-10">
      <div className="max-w-4xl mx-auto px-4">
        <div className={`rounded-3xl p-8 flex flex-col md:flex-row items-center justify-between gap-8 relative overflow-hidden ${
          isDark 
            ? "bg-gradient-to-r from-zinc-900 via-zinc-900 border border-zinc-800" 
            : "bg-gradient-to-r from-zinc-50 via-white border border-zinc-200 shadow-sm"
        }`}>
          <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-[80px]" />

          <div className="flex gap-6 items-center flex-1 relative z-10">
            <div className="w-16 h-16 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0">
              <ShieldCheck className="w-8 h-8 text-blue-500" />
            </div>
            <div>
              <h3 className={`text-xl md:text-2xl font-bold mb-2 ${isDark ? "text-white" : "text-zinc-900"}`}>
                {t.security.title}
              </h3>
              <p className={`text-sm leading-relaxed max-w-lg ${isDark ? "text-zinc-400" : "text-zinc-500"}`}>
                {t.security.desc}
              </p>
            </div>
          </div>

          <div className={`shrink-0 rounded-xl px-5 py-3 flex items-center justify-center gap-2 relative z-10 m-auto md:m-0 w-full md:w-auto ${
            isDark 
              ? "bg-black/40 border border-zinc-800" 
              : "bg-zinc-100 border border-zinc-200"
          }`}>
            <Cpu className="w-4 h-4 text-zinc-500" />
            <span className={`text-sm font-semibold ${isDark ? "text-zinc-300" : "text-zinc-700"}`}>
              {t.security.badge}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
