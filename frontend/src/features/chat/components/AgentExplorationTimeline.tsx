"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BrainCircuit, CheckCircle2, ChevronDown, Sparkles } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";

interface AgentExplorationTimelineProps {
  steps: string[];
  isStreaming: boolean;
}

export function AgentExplorationTimeline({ steps, isStreaming }: AgentExplorationTimelineProps) {
  const { theme } = useApp();
  const isDark = theme === "dark";
  const [isOpen, setIsOpen] = useState(isStreaming || steps.length > 0);
  const [prevStepCount, setPrevStepCount] = useState(steps.length);
  const [prevStreaming, setPrevStreaming] = useState(isStreaming);

  // 새로운 스텝이 추가되거나 스트리밍이 시작되면 자동으로 열림
  if (steps.length > prevStepCount || (isStreaming && !prevStreaming)) {
    setPrevStepCount(steps.length);
    setPrevStreaming(isStreaming);
    if (!isOpen) setIsOpen(true);
  } else if (!isStreaming && prevStreaming) {
    setPrevStreaming(isStreaming);
  }

  if (!steps || steps.length === 0) return null;

  return (
    <div className={`mb-4 flex flex-col gap-2 rounded-xl border p-3 backdrop-blur-md transition-colors ${isDark ? "border-zinc-800/60 bg-zinc-900/30" : "border-indigo-100 bg-indigo-50/50"}`}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between group cursor-pointer select-none"
      >
        <div className={`flex items-center gap-2 text-xs font-semibold ${isDark ? "text-blue-400" : "text-indigo-600"}`}>
          <BrainCircuit className="size-4" />
          <span>멀티에이전트 자율 탐색 ({steps.length})</span>
          {isStreaming && (
            <span className="relative flex size-2 ml-1">
              <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${isDark ? "bg-blue-400" : "bg-indigo-400"}`}></span>
              <span className={`relative inline-flex size-2 rounded-full ${isDark ? "bg-blue-500" : "bg-indigo-500"}`}></span>
            </span>
          )}
        </div>
        <ChevronDown 
          className={`size-4 transition-transform duration-300 ${isOpen ? "rotate-180" : ""} ${isDark ? "text-zinc-500 group-hover:text-zinc-300" : "text-zinc-400 group-hover:text-zinc-600"}`} 
        />
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-3 flex flex-col gap-3 pl-1 pb-1">
              {steps.map((step, idx) => {
                const isLast = idx === steps.length - 1;
                return (
                  <motion.div 
                    key={`${idx}-${step}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.05 }}
                    className={`relative flex items-start gap-3 text-[11.5px] ${isDark ? "text-zinc-300" : "text-zinc-700"}`}
                  >
                    {!isLast || isStreaming ? (
                      <div className={`absolute left-[7px] top-4 bottom-[-16px] w-[1.5px] ${isDark ? "bg-zinc-800" : "bg-indigo-200"}`} />
                    ) : null}
                    
                    <div className={`relative z-10 mt-[3px] flex size-4 shrink-0 items-center justify-center rounded-full border ${isDark ? "bg-zinc-900 border-zinc-700" : "bg-white border-indigo-200"}`}>
                      <CheckCircle2 className={`size-[10px] ${isDark ? "text-green-400" : "text-green-500"}`} />
                    </div>
                    
                    <div className={`flex-1 rounded-lg border px-3 py-2 shadow-sm ${isDark ? "border-zinc-800/80 bg-zinc-900/60" : "border-white bg-white/80"}`}>
                      <span className="font-mono text-[10.5px] opacity-80 mr-1.5">[Step {idx + 1}]</span>
                      {step}
                    </div>
                  </motion.div>
                );
              })}
              
              {isStreaming && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className={`relative flex items-start gap-3 text-[11.5px] ${isDark ? "text-zinc-500" : "text-zinc-400"}`}
                >
                  <div className={`relative z-10 mt-[3px] flex size-4 shrink-0 items-center justify-center rounded-full border ${isDark ? "bg-zinc-900/50 border-zinc-800" : "bg-indigo-50/50 border-indigo-100"}`}>
                    <Sparkles className="size-[9px] animate-pulse" />
                  </div>
                  <div className="flex-1 italic pt-0.5">
                    에이전트 추론 및 다음 계획 수립 중...
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
