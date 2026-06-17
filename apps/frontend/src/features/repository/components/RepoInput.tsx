"use client";

import { useEffect, useId, useMemo, useState } from "react";
import type { LlmModel, ProviderCatalog } from "@/common/types/contracts";
import { Github, FolderOpen, RefreshCw, ChevronDown } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";
import { apiPath } from "@/features/analysis/api/api";

export type RepoSource = "local" | "github";

const PROVIDER_BADGES: Record<
  ProviderCatalog["provider"],
  { label: string; color: string }
> = {
  openai: { label: "OpenAI", color: "bg-zinc-800 text-zinc-200 border-zinc-700" },
  deepseek: { label: "DeepSeek", color: "bg-blue-500/10 text-blue-300 border-blue-500/30" },
  qwen: { label: "Qwen", color: "bg-purple-500/10 text-purple-300 border-purple-500/30" },
  zhipu: { label: "GLM", color: "bg-indigo-500/10 text-indigo-300 border-indigo-500/30" },
  moonshot: { label: "Kimi", color: "bg-pink-500/10 text-pink-300 border-pink-500/30" },
  custom: { label: "Custom", color: "bg-zinc-800 text-zinc-200 border-zinc-700" },
};

export interface RepoInputProps {
  onSubmit: (input: {
    source: RepoSource;
    path: string;
    force_refresh?: boolean;
    model?: LlmModel;
  }) => void;
  disabled?: boolean;
  defaultMode?: RepoSource;
}

const WINDOWS_PATH = /^[a-zA-Z]:[\\/](?:[^<>:"|?*\r\n]+[\\/]?)*$/;
const UNIX_PATH = /^\/(?:[^<>:"|?*\r\n\0]+\/?)*$/;
const GITHUB_URL = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+?(?:\.git)?\/?$/;

function validate(mode: RepoSource, value: string, t: any): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return mode === "github" ? t.repoInput.errorGithubEmpty : t.repoInput.errorLocalEmpty;
  }
  if (mode === "github") {
    return GITHUB_URL.test(trimmed)
      ? null
      : t.repoInput.errorGithubInvalid;
  }
  return WINDOWS_PATH.test(trimmed) || UNIX_PATH.test(trimmed)
    ? null
    : t.repoInput.errorLocalInvalid;
}

export function RepoInput({
  onSubmit,
  disabled = false,
  defaultMode = "local",
}: RepoInputProps) {
  const [mode, setMode] = useState<RepoSource>(defaultMode);
  const [value, setValue] = useState("");
  const [touched, setTouched] = useState(false);
  const [forceRefresh, setForceRefresh] = useState(false);
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [selectedModel, setSelectedModel] = useState<LlmModel>("");
  
  const { theme, t } = useApp();
  const isDark = theme === "dark";

  const inputId = useId();
  const forceId = useId();
  const modelId = useId();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetch(apiPath("/models"));
        if (!resp.ok) return;
        const data = (await resp.json()) as ProviderCatalog;
        if (cancelled) return;
        setCatalog(data);
        setSelectedModel(data.default_model || data.models[0]?.id || "");
      } catch {
        // Fallback or ignore
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const error = useMemo(
    () => (touched ? validate(mode, value, t) : null),
    [mode, value, touched, t],
  );

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setTouched(true);
    const err = validate(mode, value, t);
    if (err) return;
    onSubmit({
      source: mode,
      path: value.trim(),
      force_refresh: forceRefresh,
      model: selectedModel || undefined,
    });
  };

  const switchMode = (next: RepoSource) => {
    setMode(next);
    setTouched(false);
    setValue("");
  };

  const cardClass = isDark ? 'bg-zinc-900/60 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm';
  const titleClass = isDark ? 'text-white' : 'text-zinc-900';
  const subtitleClass = isDark ? 'text-zinc-500' : 'text-zinc-400';
  const labelClass = isDark ? 'text-zinc-400' : 'text-zinc-500';
  const inputClass = isDark ? 'bg-zinc-950 border-zinc-700 text-white placeholder:text-zinc-600 focus:border-blue-500' : 'bg-white border-zinc-300 text-zinc-900 placeholder:text-zinc-400 focus:border-blue-500';
  const tabContainerClass = isDark ? 'bg-zinc-950/80 border-zinc-800' : 'bg-zinc-100 border-zinc-200';
  const checkboxContainerClass = isDark ? 'bg-zinc-950/50 border-zinc-800' : 'bg-zinc-50 border-zinc-200';
  const submitClass = isDark ? 'bg-white text-black hover:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-500' : 'bg-black text-white hover:bg-zinc-800 disabled:bg-zinc-200 disabled:text-zinc-400';

  return (
    <div className={`border rounded-2xl p-5 backdrop-blur-sm transition-colors ${cardClass}`}>
      <div className="mb-4">
        <h2 className={`text-sm font-semibold ${titleClass}`}>{t.repoInput.title}</h2>
        <p className={`text-[11px] mt-0.5 leading-relaxed ${subtitleClass}`}>
          {t.repoInput.subtitle}
        </p>
      </div>

      {/* Mode Tabs */}
      <div
        className={`mb-4 inline-flex p-1 rounded-xl border transition-colors ${tabContainerClass}`}
        role="tablist"
        aria-label="Input mode selection"
      >
        {(["local", "github"] as const).map((m) => {
          const isActive = mode === m;
          const activeClass = isDark ? 'bg-white text-black shadow-sm' : 'bg-black text-white shadow-sm';
          const inactiveClass = isDark ? 'text-zinc-500 hover:text-zinc-300' : 'text-zinc-400 hover:text-zinc-600';
          return (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => switchMode(m)}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-semibold transition-all duration-150 ${
                isActive ? activeClass : inactiveClass
              }`}
            >
              {m === "github" ? (
                <><Github className="w-3 h-3" /> {t.repoInput.tabGithub}</>
              ) : (
                <><FolderOpen className="w-3 h-3" /> {t.repoInput.tabLocal}</>
              )}
            </button>
          )
        })}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Path Input */}
        <div>
          <label htmlFor={inputId} className={`block text-[11px] font-semibold mb-1.5 uppercase tracking-wide ${labelClass}`}>
            {mode === "github" ? t.repoInput.labelGithub : t.repoInput.labelLocal}
          </label>
          <input
            id={inputId}
            type="text"
            value={value}
            placeholder={
              mode === "github"
                ? t.repoInput.placeholderGithub
                : t.repoInput.placeholderLocal
            }
            onChange={(e) => setValue(e.target.value)}
            onBlur={() => setTouched(true)}
            disabled={disabled}
            aria-invalid={error ? "true" : "false"}
            aria-describedby={error ? `${inputId}-error` : undefined}
            className={`w-full text-sm px-3 py-2.5 rounded-xl border focus:outline-none focus:ring-1 transition-all disabled:opacity-50 disabled:cursor-not-allowed focus:ring-blue-500 ${inputClass}`}
          />
          {error && (
            <p id={`${inputId}-error`} className="text-[11px] text-red-400 mt-1.5 font-medium">
              {error}
            </p>
          )}
        </div>

        {/* Model Select */}
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label htmlFor={modelId} className={`text-[11px] font-semibold uppercase tracking-wide ${labelClass}`}>
              {t.repoInput.modelLabel}
            </label>
            {catalog && (
              <span
                className={`rounded border px-1.5 py-0.5 text-[9px] font-bold tracking-wide uppercase ${
                  PROVIDER_BADGES[catalog.provider].color
                }`}
              >
                {PROVIDER_BADGES[catalog.provider].label}
              </span>
            )}
          </div>
          <div className="relative">
            <select
              id={modelId}
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value as LlmModel)}
              disabled={disabled || !catalog}
              className={`w-full appearance-none rounded-xl border px-3 py-2.5 pr-8 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed ${inputClass}`}
            >
              {!catalog && <option value="">Loading models...</option>}
              {catalog?.models.map((m) => (
                <option key={m.id} value={m.id} className={isDark ? "bg-zinc-950 text-white" : "bg-white text-zinc-900"}>
                  {m.label}
                </option>
              ))}
            </select>
            <ChevronDown className={`absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 pointer-events-none ${isDark ? "text-zinc-500" : "text-zinc-400"}`} />
          </div>
          {catalog && (
            <p className={`mt-1 text-[10px] leading-normal ${isDark ? "text-zinc-600" : "text-zinc-500"}`}>
              {catalog.models.find((m) => m.id === selectedModel)?.hint}
            </p>
          )}
        </div>

        {/* Cache Bypass */}
        <div className={`flex items-start gap-2.5 p-3 rounded-xl border transition-colors ${checkboxContainerClass}`}>
          <input
            id={forceId}
            type="checkbox"
            checked={forceRefresh}
            onChange={(e) => setForceRefresh(e.target.checked)}
            disabled={disabled}
            className={`mt-0.5 h-3.5 w-3.5 rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer border-zinc-600 ${isDark ? "bg-zinc-900" : "bg-white"}`}
          />
          <div>
            <label htmlFor={forceId} className={`text-[11px] cursor-pointer select-none font-medium ${labelClass}`}>
              {t.repoInput.cacheLabel}
            </label>
            <p className={`text-[10px] mt-0.5 ${isDark ? "text-zinc-600" : "text-zinc-500"}`}>{t.repoInput.cacheHint}</p>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={disabled}
          className={`w-full py-3 px-4 text-sm font-bold rounded-xl transition-all duration-150 shadow-sm ${submitClass}`}
        >
          {disabled ? (
            <span className="flex items-center justify-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              {t.repoInput.submitting}
            </span>
          ) : (
            t.repoInput.submit
          )}
        </button>
      </form>
    </div>
  );
}
