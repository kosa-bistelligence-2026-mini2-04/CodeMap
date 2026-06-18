"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import { Terminal, Code2, BrainCircuit, CheckCircle2, ShieldAlert, GitMerge, ChevronLeft, ChevronRight, Network } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";

function TypewriterText({ text, step }: { text: string; step: number }) {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    if (step !== 1) return;

    let i = 0;
    const speed = 1500 / text.length;
    const interval = setInterval(() => {
      setDisplayedText(text.substring(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(interval);
    }, speed);

    return () => clearInterval(interval);
  }, [text, step]);

  return (
    <span className="whitespace-pre-wrap break-words">
      {step === 0 ? "" : step >= 2 ? text : displayedText}
      {(step === 0 || step === 1) && (
        <span className="inline-block w-[2px] h-[1em] bg-blue-500 animate-pulse align-middle ml-[2px]" />
      )}
    </span>
  );
}

export function InteractiveDemo() {
  const [step, setStep] = useState(0);
  const [scenarioIndex, setScenarioIndex] = useState(0);
  const [playbackKey, setPlaybackKey] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: false, margin: "-100px" });
  const { theme, t } = useApp();
  const isDark = theme === "dark";
  const scenarioCount = t.demo.scenarios.length;

  // Derive scenarios array with translated text
  const scenarios = [
    {
      id: "analyze",
      title: t.demo.scenarios[0].title,
      query: t.demo.scenarios[0].query,
      loadingText: t.demo.scenarios[0].loadingText,
      analyzingText: t.demo.scenarios[0].analyzingText,
      tags: [
        { icon: Code2, text: "fastapi/dependencies/utils.py", color: "text-green-400" },
        { icon: Code2, text: "fastapi/routing.py", color: "text-green-400" },
      ],
      type: "chat",
      translationData: t.demo.scenarios[0]
    },
    {
      id: "architecture",
      title: t.demo.scenarios[1].title,
      query: t.demo.scenarios[1].query,
      loadingText: t.demo.scenarios[1].loadingText,
      analyzingText: t.demo.scenarios[1].analyzingText,
      tags: [
        { icon: GitMerge, text: "numpy/core/_multiarray_umath.py", color: "text-blue-400" },
        { icon: Network, text: "numpy/linalg/__init__.py", color: "text-blue-400" },
      ],
      type: "architecture",
      translationData: t.demo.scenarios[1]
    },
    {
      id: "security",
      title: t.demo.scenarios[2].title,
      query: t.demo.scenarios[2].query,
      loadingText: t.demo.scenarios[2].loadingText,
      analyzingText: t.demo.scenarios[2].analyzingText,
      tags: [
        { icon: ShieldAlert, text: "requests/utils.py", color: "text-red-400" },
      ],
      type: "security",
      translationData: t.demo.scenarios[2]
    }
  ];

  const handleManualSwitch = (dir: 'next' | 'prev') => {
    if (dir === 'next') {
      setScenarioIndex((prev) => (prev + 1) % scenarios.length);
    } else {
      setScenarioIndex((prev) => (prev === 0 ? scenarios.length - 1 : prev - 1));
    }
    setStep(0);
    setPlaybackKey(k => k + 1);
  };

  useEffect(() => {
    const sequence = [
      { step: 1, delay: 1000 },
      { step: 2, delay: 2500 },
      { step: 3, delay: 1500 },
      { step: 4, delay: 2000 },
      { step: 5, delay: 6000 },
      { step: 0, delay: 1000 },
    ];

    if (!isInView) return;

    let timer: NodeJS.Timeout;
    const runSequence = (index: number) => {
      const nextIndex = index >= sequence.length ? 0 : index;
      setStep(sequence[nextIndex].step);
      if (nextIndex === 0 && index !== 0) {
        setScenarioIndex((prev) => (prev + 1) % scenarioCount);
      }
      timer = setTimeout(() => runSequence(nextIndex + 1), sequence[nextIndex].delay);
    };

    timer = setTimeout(() => runSequence(0), 1000);
    return () => clearTimeout(timer);
  }, [isInView, playbackKey, scenarioCount]);

  const currentScenario = scenarios[scenarioIndex];
  const visibleStep = isInView ? step : 0;

  const renderResponse = () => {
    if (currentScenario.type === "chat") {
      const tData = currentScenario.translationData;
      if (!("chatPart1" in tData)) return null;
      return (
        <div className="space-y-3 font-sans text-sm leading-relaxed">
          <p>
            {tData.chatPart1} <span className="text-white font-medium">{tData.chatPart1Bold}</span>{tData.chatPart1End} <span className="text-blue-400 font-mono text-xs bg-blue-900/20 px-1 rounded">{tData.chatPart1Code}</span> {tData.chatPart1Tail}
          </p>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
          >
            {tData.chatPart2}
          </motion.p>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 1.5 }}
            className="mt-4 bg-black/40 p-3 rounded-lg border border-zinc-800 border-l-4 border-l-purple-500"
          >
            <div className="flex items-center gap-2 text-purple-400 text-xs font-semibold mb-2">
              <CheckCircle2 className="w-3 h-3" />
              <span>{tData.badgeTitle}</span>
            </div>
            <code className="text-xs text-zinc-400 block overflow-hidden break-words whitespace-pre-wrap bg-black/50 p-2 rounded mt-2">
              <span className="text-pink-400">async def</span> <span className="text-blue-300">get_db</span>():{'\n'}
              &nbsp;&nbsp;<span className="text-pink-400">yield</span> SessionLocal(){'\n'}
              <span className="text-zinc-500"># Injected via Depends(get_db)</span>
            </code>
          </motion.div>
        </div>
      );
    }

    if (currentScenario.type === "architecture") {
      const tData = currentScenario.translationData;
      if (!("archText" in tData)) return null;
      return (
        <div className="space-y-3 font-sans text-sm leading-relaxed">
          <p>
            {tData.archText}
          </p>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-4 bg-zinc-900 overflow-hidden rounded-lg border border-zinc-700"
          >
            <div className="p-4 flex flex-col items-center gap-2 text-xs font-mono text-blue-300">
              <div className="border border-blue-500/50 bg-blue-900/20 px-4 py-2 rounded">{tData.archEntry}</div>
              <div className="h-4 border-l border-blue-500/50"></div>
              <div className="border border-purple-500/50 bg-purple-900/20 px-4 py-2 rounded text-purple-300">{tData.archCore}</div>
              <div className="h-4 border-l border-purple-500/50"></div>
              <div className="border border-green-500/50 bg-green-900/20 px-4 py-2 rounded text-green-300">{tData.archModules}</div>
            </div>
          </motion.div>
        </div>
      );
    }

    if (currentScenario.type === "security") {
      const tData = currentScenario.translationData;
      if (!("secText" in tData)) return null;
      return (
        <div className="space-y-3 font-sans text-sm leading-relaxed">
          <p>
            {tData.secText}
          </p>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-4 bg-green-950/20 p-3 rounded-lg border border-green-900/50 border-l-4 border-l-green-500"
          >
            <div className="flex items-center gap-2 text-green-500 text-xs font-semibold mb-2">
              <CheckCircle2 className="w-3 h-3" />
              <span>{tData.secBadge}</span>
            </div>
            <p className="text-zinc-300 text-xs">{tData.secDesc}</p>
          </motion.div>
        </div>
      )
    }
  };

  return (
    <section ref={containerRef} className="py-20 px-4 relative z-10 w-full max-w-5xl mx-auto flex flex-col items-center">
      <div className="text-center mb-10">
        <h2 className={`text-3xl md:text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r ${isDark ? "from-white to-zinc-400" : "from-zinc-900 to-zinc-500"}`}>
          {t.demo.title}
        </h2>
        <div className="flex items-center justify-center gap-6 mb-6">
          <button
            onClick={() => handleManualSwitch('prev')}
            className={`p-1.5 rounded-full transition-colors ${isDark ? "hover:bg-zinc-800 text-zinc-500 hover:text-white" : "hover:bg-zinc-200 text-zinc-400 hover:text-zinc-900"}`}
            aria-label="Previous scenario"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="flex gap-2">
            {scenarios.map((_, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setScenarioIndex(idx);
                  setStep(0);
                  setPlaybackKey(k => k + 1);
                }}
                className={`h-1.5 rounded-full transition-all duration-500 ${idx === scenarioIndex ? "w-8 bg-blue-500" : `w-3 ${isDark ? "bg-zinc-800 hover:bg-zinc-700" : "bg-zinc-300 hover:bg-zinc-400"}`}`}
                aria-label={`Go to scenario ${idx + 1}`}
              />
            ))}
          </div>
          <button
            onClick={() => handleManualSwitch('next')}
            className={`p-1.5 rounded-full transition-colors ${isDark ? "hover:bg-zinc-800 text-zinc-500 hover:text-white" : "hover:bg-zinc-200 text-zinc-400 hover:text-zinc-900"}`}
            aria-label="Next scenario"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
        <p className={`text-lg md:text-xl ${isDark ? "text-zinc-400" : "text-zinc-500"}`}>
          {t.demo.subtitle}
        </p>
      </div>

      <div className="w-full relative rounded-2xl overflow-hidden bg-zinc-950 border border-zinc-800 shadow-2xl shadow-blue-900/10">
        {/* macOS window top bar */}
        <div className="flex items-center px-4 py-3 bg-zinc-900/50 border-b border-zinc-800 transition-colors duration-500">
          <div className="flex space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-400/80" />
            <div className="w-3 h-3 rounded-full bg-yellow-400/80" />
            <div className="w-3 h-3 rounded-full bg-green-400/80" />
          </div>
          <div className="mx-auto flex items-center space-x-2 text-xs text-zinc-400 font-medium">
            <Terminal className="w-3 h-3" />
            <AnimatePresence mode="wait">
              <motion.span
                key={currentScenario.id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
              >
                {currentScenario.title}
              </motion.span>
            </AnimatePresence>
          </div>
        </div>

        {/* Content Area */}
        <div className="p-6 md:p-8 space-y-6 min-h-[450px] overflow-hidden flex flex-col">
          {/* User Query Bubble */}
          <div className="flex gap-4 items-start w-full">
            <div className="p-2 bg-blue-500/10 rounded-lg shrink-0 border border-blue-500/20 overflow-hidden">
              <div className="w-6 h-6 rounded-sm bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-[10px] font-bold text-white">U</div>
            </div>
            <div className="bg-zinc-900/60 border border-zinc-800 p-4 rounded-xl rounded-tl-none w-full text-zinc-300 font-mono text-sm shadow-sm relative">
              <div className="relative w-full">
                <TypewriterText text={currentScenario.query} step={visibleStep} />
              </div>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {/* AI Status / Thinking state */}
            {visibleStep >= 2 && visibleStep <= 3 && (
              <motion.div
                key={`status-${currentScenario.id}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center gap-3 text-sm text-zinc-500 italic pl-14"
              >
                <motion.div>
                  <BrainCircuit className="w-4 h-4 text-purple-400" />
                </motion.div>
                <span>{visibleStep === 2 ? currentScenario.loadingText : currentScenario.analyzingText}</span>
              </motion.div>
            )}

            {/* AI Response Box */}
            {visibleStep >= 4 && (
              <motion.div
                key={`response-${currentScenario.id}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex gap-4 items-start w-full"
              >
                <div className="p-1 bg-zinc-900 rounded-lg shrink-0 border border-zinc-700 shadow-[0_0_15px_rgba(255,255,255,0.05)] overflow-hidden flex items-center justify-center w-10 h-10">
                  <BrainCircuit className="w-5 h-5 text-blue-400" />
                </div>

                <div className="flex-1 space-y-4">
                  {/* Referenced Files tags */}
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="flex flex-wrap gap-2 mb-2"
                  >
                    {currentScenario.tags.map((tag, i) => {
                      const TagIcon = tag.icon;
                      return (
                        <span key={i} className="flex items-center gap-1.5 text-xs bg-zinc-800 border border-zinc-700 text-zinc-300 px-2 py-1 rounded-md">
                          <TagIcon className={`w-3 h-3 ${tag.color}`} />
                          {tag.text}
                        </span>
                      )
                    })}
                  </motion.div>

                  <div className="bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-800 p-5 rounded-2xl rounded-tl-none w-full text-zinc-300 shadow-sm relative overflow-hidden">
                    {/* Dynamic accent line */}
                    <div className={`absolute left-0 top-0 bottom-0 w-1 ${currentScenario.type === "chat" ? "bg-purple-500/20" :
                      currentScenario.type === "architecture" ? "bg-blue-500/20" :
                        "bg-green-500/20"
                      }`} />

                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.8 }}
                    >
                      {renderResponse()}
                    </motion.div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Glow Effects */}
        <div className={`absolute top-1/2 left-1/4 w-32 h-32 blur-[60px] rounded-full pointer-events-none transition-colors duration-1000 ${currentScenario.type === "chat" ? "bg-blue-500/10" :
          currentScenario.type === "architecture" ? "bg-purple-500/10" :
            "bg-green-500/10"
          }`} />
        <div className={`absolute bottom-1/4 right-1/4 w-32 h-32 blur-[60px] rounded-full pointer-events-none transition-colors duration-1000 ${currentScenario.type === "chat" ? "bg-purple-500/10" :
          currentScenario.type === "architecture" ? "bg-blue-500/10" :
            "bg-cyan-500/10"
          }`} />
      </div>
    </section>
  );
}
