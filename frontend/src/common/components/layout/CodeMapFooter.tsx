"use client";

import Link from "next/link";
import { Github, Globe, Zap, ArrowUpRight } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";

export function CodeMapFooter() {
  const { theme, t } = useApp();
  const isDark = theme === "dark";

  return (
    <footer className={`relative z-10 border-t pt-16 pb-8 overflow-hidden ${
      isDark ? "bg-[#09090b] border-white/5" : "bg-zinc-50 border-zinc-200"
    }`}>
      {/* Background Decorative Elements */}
      <div className={`absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-6xl h-px bg-gradient-to-r from-transparent to-transparent ${
        isDark ? "via-cyan-500/50" : "via-blue-500/20"
      }`} />
      <div className={`absolute top-0 left-1/4 w-64 h-64 rounded-full blur-[120px] -translate-y-1/2 ${
        isDark ? "bg-blue-600/5" : "bg-blue-600/3"
      }`} />
      <div className={`absolute top-0 right-1/4 w-64 h-64 rounded-full blur-[120px] -translate-y-1/2 ${
        isDark ? "bg-cyan-600/5" : "bg-blue-600/3"
      }`} />

      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 pb-16">
          {/* Brand Section */}
          <div className="lg:col-span-5 space-y-6">
            <Link href="/" className="flex items-center gap-3 group">
              <div>
                <h2 className={`text-xl font-bold tracking-tight transition-colors ${
                  isDark ? "text-white group-hover:text-cyan-400" : "text-zinc-900 group-hover:text-cyan-600"
                }`}>CodeMap AI</h2>
                <p className="text-zinc-500 text-xs font-medium uppercase tracking-widest">{t.footer.tagline}</p>
              </div>
            </Link>

            <p className={`text-sm leading-relaxed max-w-sm ${isDark ? "text-zinc-400" : "text-zinc-500"}`}>
              {t.footer.desc}
            </p>

            <div className="flex items-center gap-4">
              <a
                href="https://github.com"
                className={`p-2.5 rounded-lg border transition-all ${
                  isDark 
                    ? "bg-zinc-900/50 border-white/5 text-zinc-400 hover:text-white hover:border-white/20 hover:bg-zinc-800" 
                    : "bg-zinc-100 border-zinc-200 text-zinc-400 hover:text-zinc-900 hover:border-zinc-300 hover:bg-zinc-200"
                }`}
                aria-label="GitHub"
              >
                <Github className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Links Sections */}
          <div className="lg:col-span-4 grid grid-cols-2 gap-8">
            {/* Features */}
            <div className="space-y-4">
              <h3 className={`text-sm font-semibold tracking-wide uppercase ${isDark ? "text-white" : "text-zinc-900"}`}>
                {t.footer.featuresTitle}
              </h3>
              <ul className="space-y-3">
                {[
                  { name: t.footer.features[0], href: "/analyze" },
                  { name: t.footer.features[1], href: "/analyze" },
                  { name: t.footer.features[2], href: "/analyze" },
                  { name: t.footer.features[3], href: "/analyze" },
                ].map((link) => (
                  <li key={link.name}>
                    <Link href={link.href} className={`text-sm transition-colors ${
                      isDark ? "text-zinc-400 hover:text-cyan-400" : "text-zinc-500 hover:text-blue-600"
                    }`}>
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            {/* Resources */}
            <div className="space-y-4">
              <h3 className={`text-sm font-semibold tracking-wide uppercase ${isDark ? "text-white" : "text-zinc-900"}`}>
                {t.footer.resourcesTitle}
              </h3>
              <ul className="space-y-3">
                {[
                  { name: t.footer.resources[0], href: "/" },
                  { name: t.footer.resources[1], href: "/docs" },
                  { name: t.footer.resources[2], href: "https://github.com", external: true },
                ].map((link) => (
                  <li key={link.name}>
                    {link.external ? (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`text-sm transition-colors flex items-center gap-1 group ${
                          isDark ? "text-zinc-400 hover:text-cyan-400" : "text-zinc-500 hover:text-blue-600"
                        }`}
                      >
                        {link.name}
                        <ArrowUpRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                      </a>
                    ) : (
                      <Link href={link.href} className={`text-sm transition-colors ${
                        isDark ? "text-zinc-400 hover:text-cyan-400" : "text-zinc-500 hover:text-blue-600"
                      }`}>
                        {link.name}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* CTA Section */}
          <div className="lg:col-span-3 space-y-6">
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-1000 group-hover:duration-200" />
              <div className={`relative rounded-2xl p-5 space-y-4 ${
                isDark ? "bg-zinc-950 border border-white/10" : "bg-white border border-zinc-200 shadow-sm"
              }`}>
                <div className="space-y-1">
                  <h4 className={`font-medium flex items-center gap-2 ${isDark ? "text-white" : "text-zinc-900"}`}>
                    <Zap className="w-4 h-4 text-cyan-400 fill-cyan-400/20" />
                    {t.footer.ctaTitle}
                  </h4>
                  <p className="text-zinc-500 text-xs">{t.footer.ctaDesc}</p>
                </div>
                <Link
                  href="/analyze"
                  className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl transition-all font-semibold text-sm shadow-[0_2px_10px_rgba(255,255,255,0.1)] active:scale-[0.98] ${
                    isDark ? "bg-white text-black hover:bg-zinc-200" : "bg-black text-white hover:bg-zinc-800"
                  }`}
                >
                  {t.footer.ctaButton}
                </Link>
              </div>
            </div>

            {/* Status Widget */}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full border w-fit ${
              isDark ? "bg-zinc-900/50 border-white/5" : "bg-zinc-100 border-zinc-200"
            }`}>
              <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
              <span className={`text-[10px] font-medium uppercase tracking-widest ${
                isDark ? "text-zinc-400" : "text-zinc-500"
              }`}>{t.footer.statusOk}</span>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className={`pt-8 border-t flex flex-col md:flex-row items-center justify-between gap-6 ${
          isDark ? "border-white/5" : "border-zinc-200"
        }`}>
          <div className="flex flex-col md:flex-row items-center gap-4 md:gap-8">
            <p className={`text-[11px] font-medium tracking-tight ${
              isDark ? "text-zinc-600" : "text-zinc-400"
            }`}>
              © {new Date().getFullYear()} {t.footer.copyright}
            </p>
            <div className={`flex items-center gap-4 text-[11px] font-medium ${
              isDark ? "text-zinc-500" : "text-zinc-400"
            }`}>
              <span className="flex items-center gap-1.5 cursor-default hover:text-zinc-300 transition-colors">
                <Globe className="w-3 h-3" />
                {t.footer.localFirst}
              </span>
              <span className={`hidden sm:inline w-1 h-1 rounded-full ${
                isDark ? "bg-zinc-800" : "bg-zinc-300"
              }`} />
              <span className="flex items-center gap-1.5 cursor-default hover:text-zinc-300 transition-colors">
                <Zap className="w-3 h-3" />
                {t.footer.multiAgent}
              </span>
            </div>
          </div>

          <div className={`flex items-center gap-2 transition-colors cursor-pointer group ${
            isDark ? "text-zinc-500 hover:text-zinc-300" : "text-zinc-400 hover:text-zinc-600"
          }`}>
            <span className={`text-[11px] font-medium transition-colors ${
              isDark ? "group-hover:text-white" : "group-hover:text-zinc-900"
            }`}>{t.footer.poweredBy}</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
