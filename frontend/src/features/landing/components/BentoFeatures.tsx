"use client";

import { motion } from "framer-motion";
import { GitBranch, Shield, Activity, Layers, Code2, Network, Search } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";

export function BentoFeatures() {
  const { theme, t } = useApp();
  const isDark = theme === "dark";

  const cardClass = isDark
    ? "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700"
    : "bg-white/80 border-zinc-200 hover:border-zinc-300 shadow-sm";
  const textPrimary = isDark ? "text-white" : "text-zinc-900";
  const textSec = isDark ? "text-zinc-400" : "text-zinc-500";
  const titleGradient = isDark 
    ? "from-white to-white/60" 
    : "from-zinc-900 to-zinc-600";
  const codeMockBg = isDark ? "bg-black/50 border-zinc-800" : "bg-zinc-50 border-zinc-200";

  return (
    <section className="w-full max-w-7xl mx-auto px-4 py-24 relative z-10">
      <div className="text-center mb-16">
        <h2 className={`text-4xl md:text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-b ${titleGradient}`}>
          {t.bento.title}
        </h2>
        <p className={`text-lg md:text-xl max-w-2xl mx-auto mb-12 ${textSec}`}>
          {t.bento.subtitle}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6 auto-rows-[minmax(200px,auto)]">

        {/* 1. Deep Code Analysis - Large */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className={`col-span-1 md:col-span-2 lg:col-span-2 row-span-2 rounded-3xl p-8 flex flex-col justify-between relative overflow-hidden group transition-colors border ${cardClass}`}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

          <div className="relative z-10">
            <div className="w-12 h-12 rounded-2xl bg-blue-500/20 flex items-center justify-center mb-6">
              <Code2 className="w-6 h-6 text-blue-400" />
            </div>
            <h3 className={`text-2xl font-bold mb-3 ${textPrimary}`}>{t.bento.features[0].title}</h3>
            <p className={`text-sm leading-relaxed max-w-sm ${textSec}`}>
              {t.bento.features[0].desc}
            </p>
          </div>

          {/* Decorative Background */}
          <div className={`absolute bottom-0 right-0 w-2/3 h-1/2 bg-gradient-to-t from-blue-900/20 to-transparent border-t border-l border-blue-500/20 rounded-tl-2xl shadow-[-20px_-20px_30px_rgba(59,130,246,0.05)] text-[10px] font-mono p-4 overflow-hidden pointer-events-none ${isDark ? "text-blue-300/30" : "text-blue-700/30"}`}>
            {'// Static analysis complete'}<br />
            {'const map = await CodeMap.analyze();'}<br />
            {'map.modules.forEach(m => {'}<br />
            &nbsp;&nbsp;{'console.log(m.dependencies);'}<br />
            {'});'}
          </div>
        </motion.div>

        {/* 2. Architecture Mapping - Medium */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className={`col-span-1 md:col-span-1 lg:col-span-2 row-span-1 rounded-3xl p-8 relative overflow-hidden group transition-colors border ${cardClass}`}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <div className="relative z-10 flex flex-col sm:flex-row gap-6 items-center">
            <div className="flex-1">
              <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center mb-4">
                <Network className="w-5 h-5 text-purple-400" />
              </div>
              <h3 className={`text-xl font-bold mb-2 ${textPrimary}`}>{t.bento.features[1].title}</h3>
              <p className={`text-sm leading-relaxed ${textSec}`}>
                {t.bento.features[1].desc}
              </p>
            </div>
            <div className={`w-full sm:w-48 rounded-xl p-3 shadow-inner border ${codeMockBg}`}>
              <div className="text-xs text-zinc-500 font-mono mb-2">{t.bento.features[1].mockLabel}</div>
              <div className={`text-sm ${isDark ? "text-zinc-300" : "text-zinc-700"}`}>{t.bento.features[1].mockValue}</div>
            </div>
          </div>
        </motion.div>

        {/* 3. Git Analysis - Small */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className={`col-span-1 md:col-span-1 lg:col-span-1 row-span-1 rounded-3xl p-6 flex flex-col relative overflow-hidden group transition-colors border ${cardClass}`}
        >
          <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center mb-4 relative z-10">
            <GitBranch className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="relative z-10">
            <h3 className={`text-lg font-bold mb-2 ${textPrimary}`}>{t.bento.features[2].title}</h3>
            <p className={`text-xs leading-relaxed ${textSec}`}>
              {t.bento.features[2].desc}
            </p>
          </div>
        </motion.div>

        {/* 4. Security Scanner - Small */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className={`col-span-1 md:col-span-1 lg:col-span-1 row-span-1 rounded-3xl p-6 flex flex-col relative overflow-hidden group transition-colors border ${cardClass}`}
        >
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Shield className="w-24 h-24 text-red-500" />
          </div>
          <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center mb-4 relative z-10">
            <Shield className="w-5 h-5 text-red-400" />
          </div>
          <div className="relative z-10 mt-auto">
            <h3 className={`text-lg font-bold mb-2 ${textPrimary}`}>{t.bento.features[3].title}</h3>
            <p className={`text-xs leading-relaxed ${textSec}`}>
              {t.bento.features[3].desc}
            </p>
          </div>
        </motion.div>

        {/* 5. Developer Intel - Medium */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className={`col-span-1 md:col-span-2 lg:col-span-2 row-span-1 rounded-3xl p-8 flex flex-col justify-center relative overflow-hidden group transition-colors border ${cardClass}`}
        >
          <div className="w-10 h-10 rounded-xl bg-pink-500/20 flex items-center justify-center mb-4 relative z-10">
            <Search className="w-5 h-5 text-pink-400" />
          </div>
          <div className="relative z-10">
            <h3 className={`text-xl font-bold mb-2 ${textPrimary}`}>{t.bento.features[4].title}</h3>
            <p className={`text-sm leading-relaxed max-w-sm ${textSec}`}>
              {t.bento.features[4].desc}
            </p>
          </div>
          <Activity className="absolute bottom-[-10%] right-[5%] w-48 h-48 text-pink-500/5 group-hover:text-pink-500/10 transition-colors duration-500 pointer-events-none" />
        </motion.div>

        {/* 6. Onboarding Reports - Medium */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
          className={`col-span-1 md:col-span-1 lg:col-span-2 row-span-1 rounded-3xl p-8 flex flex-col justify-center relative overflow-hidden group transition-colors border ${cardClass}`}
        >
          <div className="flex gap-4 items-center relative z-10">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center shrink-0">
              <Layers className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h3 className={`text-xl font-bold mb-1 ${textPrimary}`}>{t.bento.features[5].title}</h3>
              <p className={`text-sm leading-relaxed ${textSec}`}>
                {t.bento.features[5].desc}
              </p>
            </div>
          </div>
        </motion.div>

      </div>
    </section>
  );
}
