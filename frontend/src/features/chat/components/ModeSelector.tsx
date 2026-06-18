"use client";

import { motion } from "framer-motion";
import { Zap, Brain } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";
import type { ChatMode } from "@/features/chat/api/chatApi";

interface ModeSelectorProps {
  mode: ChatMode;
  onChange: (mode: ChatMode) => void;
  disabled?: boolean;
}

export function ModeSelector({ mode, onChange, disabled }: ModeSelectorProps) {
  const { t } = useApp();

  const modes = [
    {
      key: "lite" as const,
      icon: Zap,
      label: t.chat.mode.lite,
      desc: t.chat.mode.liteDesc,
      color: "var(--accent-cyan)",
    },
    {
      key: "deep" as const,
      icon: Brain,
      label: t.chat.mode.deep,
      desc: t.chat.mode.deepDesc,
      color: "var(--accent-purple)",
    },
  ];

  return (
    <div
      className="inline-flex rounded-xl p-1 gap-1"
      style={{
        background: "var(--bg-secondary)",
        border: "1px solid var(--border-primary)",
      }}
    >
      {modes.map((m) => {
        const isActive = mode === m.key;
        const Icon = m.icon;

        return (
          <button
            key={m.key}
            onClick={() => onChange(m.key)}
            disabled={disabled}
            className="relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
            style={{
              color: isActive ? m.color : "var(--text-muted)",
            }}
            title={m.desc}
          >
            {isActive && (
              <motion.div
                layoutId="mode-pill"
                className="absolute inset-0 rounded-lg"
                style={{
                  background: `color-mix(in srgb, ${m.color} 12%, transparent)`,
                  border: `1px solid color-mix(in srgb, ${m.color} 30%, transparent)`,
                }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <Icon className="w-3.5 h-3.5 relative z-10" />
            <span className="relative z-10">{m.label}</span>
          </button>
        );
      })}
    </div>
  );
}
