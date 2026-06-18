"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, Github, GitBranch, Code2, Network, Shield, ChevronDown } from "lucide-react";
import Link from "next/link";
import { AsciiScene } from "@/features/landing/components/hero/AsciiScene";
import { BentoFeatures } from "@/features/landing/components/BentoFeatures";
import { InteractiveDemo } from "@/features/landing/components/InteractiveDemo";
import { SecurityBanner } from "@/common/components/ui/SecurityBanner";
import { CodeMapFooter } from "@/common/components/layout/CodeMapFooter";
import { useApp } from "@/common/contexts/AppContext";
import { RepositoryLauncher } from "@/features/landing/components/RepositoryLauncher";
import { TrendingRepos } from "@/features/landing/components/TrendingRepos";

const EXAMPLE_REPOS = [
  { label: "fastapi/fastapi", url: "https://github.com/tiangolo/fastapi" },
  { label: "numpy/numpy", url: "https://github.com/numpy/numpy" },
  { label: "vercel/next.js", url: "https://github.com/vercel/next.js" },
];

export default function Home() {
  const [activeFaqIndex, setActiveFaqIndex] = useState<number | null>(null);
  const router = useRouter();
  const { theme, t } = useApp();

  const isDark = theme === "dark";

  const handleAnalyze = (url: string) => {
    router.push(`/analyze?path=${encodeURIComponent(url)}&source=github`);
  };

  // Theme-aware class helpers
  const sectionDark = isDark
    ? "bg-black border-white/5"
    : "bg-zinc-50 border-zinc-200/60";
  const sectionAlt = isDark
    ? "bg-zinc-950 border-white/5"
    : "bg-white border-zinc-200/60";
  const cardClass = isDark
    ? "rounded-2xl border border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"
    : "rounded-2xl border border-zinc-200 bg-white hover:border-zinc-300 shadow-sm";
  const textPrimary = isDark ? "text-white" : "text-zinc-900";
  const textSec = isDark ? "text-zinc-400" : "text-zinc-500";
  const textMuted = isDark ? "text-zinc-500" : "text-zinc-400";

  return (
    <main
      className="flex flex-col overflow-x-hidden relative"
      style={{ background: "var(--bg-primary)" }}
    >
      {/* Global background glow */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div
          className="absolute top-[-20%] left-[-10%] w-[80vw] max-w-[500px] h-[80vw] max-h-[500px] rounded-full blur-[128px]"
          style={{ background: "var(--hero-glow-1)" }}
        />
        <div
          className="absolute bottom-[-20%] right-[-10%] w-[80vw] max-w-[500px] h-[80vw] max-h-[500px] rounded-full blur-[128px]"
          style={{ background: "var(--hero-glow-2)" }}
        />
      </div>

      {/* ═══════════════════════════════════════════════
          HERO
      ═══════════════════════════════════════════════ */}
      <section className="min-h-[100svh] flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden z-10">
        <div className="ascii-scene-overlay">
          <AsciiScene isDark={isDark} />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="z-10 flex flex-col items-center text-center max-w-3xl w-full px-4 gap-3 md:gap-4"
        >
          {/* Badge */}
          <div className="w-full flex flex-col items-center gap-3">
            <p className="whitespace-nowrap text-xs md:text-sm font-semibold tracking-[0.35em] uppercase leading-none" style={{ color: "var(--text-muted)" }}>
              {t.hero.badge}
            </p>
          </div>

          <h1
            className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight"
            style={{ color: "var(--text-primary)" }}
          >
            {t.hero.title.split("\n").map((line: string, i: number) => (
              <span key={i}>
                {line}
                {i === 0 && <br />}
              </span>
            ))}
          </h1>

          <p className="text-sm sm:text-base md:text-lg max-w-2xl mx-auto leading-snug" style={{ color: "var(--text-secondary)" }}>
            {t.hero.subtitle}
          </p>

          <RepositoryLauncher onAnalyze={handleAnalyze} />

          <div className="mt-1 flex flex-wrap items-center justify-center gap-2">
            <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: "var(--text-faint)" }}>
              {t.hero.tryLabel}
            </span>
            {EXAMPLE_REPOS.map((repo) => (
              <button
                key={repo.label}
                onClick={() => handleAnalyze(repo.url)}
                className="text-xs rounded-lg px-3 py-1.5 transition-all border"
                style={{
                  color: "var(--text-secondary)",
                  borderColor: "var(--border-primary)",
                  background: "var(--bg-card)",
                }}
              >
                {repo.label}
              </button>
            ))}
          </div>

          {/* Stats Row */}
          <div className="flex items-center gap-6 md:gap-10 mt-4 text-center">
            {[
              { icon: Code2, label: t.hero.statsLanguages, value: "10+" },
              { icon: Network, label: t.hero.statsAgents, value: "4" },
              { icon: GitBranch, label: t.hero.statsDepth, value: t.hero.statsDepthValue },
              { icon: Shield, label: t.hero.statsPrivacy, value: t.hero.statsPrivacyValue },
            ].map((stat) => (
              <div key={stat.label} className="flex flex-col items-center gap-0.5">
                <stat.icon className="w-4 h-4 mb-1" style={{ color: "var(--text-faint)" }} />
                <span className="font-bold text-sm" style={{ color: "var(--text-primary)" }}>{stat.value}</span>
                <span className="text-[10px] uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{stat.label}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 flex flex-col items-center gap-1"
          style={{ color: "var(--text-faint)" }}
        >
          <span className="text-[10px] uppercase tracking-widest">{t.hero.scroll}</span>
          <ChevronDown className="w-4 h-4 animate-bounce" />
        </motion.div>
      </section>

      <div className={`relative z-10 w-full ${sectionAlt}`}>
        <TrendingRepos onAnalyze={handleAnalyze} />
      </div>

      {/* ═══════════════════════════════════════════════
          HOW IT WORKS
      ═══════════════════════════════════════════════ */}
      <section className={`relative z-10 w-full py-24 px-6 border-t ${sectionDark}`}>
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className={`text-4xl md:text-5xl font-bold tracking-tight mb-4 ${textPrimary}`}>
              {t.howItWorks.title}
            </h2>
            <p className={`text-lg max-w-3xl mx-auto ${textSec}`}>
              {t.howItWorks.subtitle}
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {t.howItWorks.steps.map((item, i) => {
              const colors = ["text-blue-400", "text-purple-400", "text-cyan-400", "text-green-400"];
              return (
                <article key={i} className={`${cardClass} p-5 relative overflow-hidden group transition-colors`}>
                  <div className={`text-5xl font-black ${colors[i]} opacity-10 absolute top-3 right-4 leading-none select-none`}>
                    {i + 1}
                  </div>
                  <h3 className={`font-semibold mb-2 ${colors[i]}`}>{i + 1}. {item.title}</h3>
                  <p className={`text-sm ${textSec}`}>{item.desc}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          INTERACTIVE DEMO
      ═══════════════════════════════════════════════ */}
      <div className={`relative z-10 w-full border-t ${sectionAlt} flex justify-center`}>
        <InteractiveDemo />
      </div>

      {/* ═══════════════════════════════════════════════
          BENTO FEATURES
      ═══════════════════════════════════════════════ */}
      <div className={`relative z-10 w-full border-t ${sectionDark} flex justify-center`}>
        <BentoFeatures />
      </div>

      {/* ═══════════════════════════════════════════════
          SECURITY BANNER
      ═══════════════════════════════════════════════ */}
      <div className={`relative z-10 w-full ${sectionAlt}`}>
        <SecurityBanner />
      </div>

      {/* ═══════════════════════════════════════════════
          USE CASES
      ═══════════════════════════════════════════════ */}
      <section className={`relative z-10 w-full py-24 px-6 border-t ${sectionAlt}`}>
        <div className="max-w-7xl mx-auto">
          <h2 className={`text-4xl md:text-5xl font-bold tracking-tight mb-5 ${textPrimary}`}>
            {t.useCases.title}
          </h2>
          <p className={`text-lg mb-8 ${textSec}`}>{t.useCases.subtitle}</p>
          <div className="space-y-4">
            {t.useCases.cases.map((c, i) => {
              const colors = ["text-cyan-500", "text-purple-500", "text-red-500"];
              return (
                <article key={i} className={`${cardClass} p-5 group transition-colors`}>
                  <h3 className={`text-xl font-semibold mb-2 group-hover:${colors[i]} transition-colors ${textPrimary}`}>
                    {c.title}
                  </h3>
                  <p className={`text-sm mb-4 ${textSec}`}>{c.desc}</p>
                  <Link href="/analyze" className={`${colors[i]} text-xs font-bold hover:opacity-70 transition-opacity flex items-center gap-1`}>
                    {c.link} <ArrowRight size={12} />
                  </Link>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          FAQ
      ═══════════════════════════════════════════════ */}
      <section className={`relative z-10 w-full py-24 px-6 border-t ${sectionDark}`}>
        <div className="max-w-5xl mx-auto">
          <h2 className={`text-4xl md:text-5xl font-bold tracking-tight mb-10 ${textPrimary}`}>
            {t.faq.title}
          </h2>
          <div className="space-y-4">
            {t.faq.items.map((item, index) => (
              <article key={index} className={`${cardClass} transition-colors`}>
                <button
                  type="button"
                  aria-expanded={activeFaqIndex === index}
                  onClick={() => setActiveFaqIndex((c) => (c === index ? null : index))}
                  className="flex w-full items-center justify-between gap-4 p-6 text-left"
                >
                  <h3 className={`text-lg font-semibold ${textPrimary}`}>{item.question}</h3>
                  <ChevronDown
                    className={`h-5 w-5 shrink-0 transition-transform ${textMuted} ${activeFaqIndex === index ? "rotate-180" : ""}`}
                  />
                </button>
                <motion.div
                  initial={false}
                  animate={activeFaqIndex === index ? { height: "auto", opacity: 1 } : { height: 0, opacity: 0 }}
                  transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
                  className="overflow-hidden will-change-[height,opacity]"
                >
                  <div className="px-6 pb-6">
                    <p className={`leading-relaxed text-sm ${textSec}`}>{item.answer}</p>
                  </div>
                </motion.div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════
          CTA
      ═══════════════════════════════════════════════ */}
      <section className={`relative z-10 w-full py-24 px-6 border-t ${sectionAlt}`}>
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-cyan-400">
            {t.cta.title}
          </h2>
          <p className={`text-lg mb-8 ${textSec}`}>{t.cta.subtitle}</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/analyze"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-2xl font-bold transition-colors group cm-btn-primary"
            >
              {t.cta.primary}
              <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              href="https://github.com"
              className={`inline-flex items-center justify-center gap-2 px-8 py-4 rounded-2xl font-bold transition-colors border ${isDark ? "bg-zinc-900 border-white/10 text-white hover:bg-zinc-800" : "bg-zinc-100 border-zinc-300 text-zinc-900 hover:bg-zinc-200"}`}
            >
              <Github size={18} />
              {t.cta.secondary}
            </Link>
          </div>
        </div>
      </section>

      <CodeMapFooter />
    </main>
  );
}
