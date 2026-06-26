"use client";

import { useId, useMemo, useState } from "react";
import { ChevronDown, Github, RefreshCw, SlidersHorizontal, Sparkles, Info } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";

export type RepoSource = "local" | "github";

interface RepoInputProps {
  onSubmit: (input: {
    source: RepoSource;
    path: string;
    branch?: string;
    force_refresh?: boolean;
    model?: string;
  }) => void;
  disabled?: boolean;
  defaultMode?: RepoSource;
  initialPath?: string;
  initialMode?: RepoSource;
}

const GITHUB_URL = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+?(?:\.git)?\/?$/;

type ModelOption = {
  id: string;
  label: string;
  tag?: "fast" | "thinking";
  disabled?: boolean;
};

const CUSTOM_MODELS: ModelOption[] = [
  { id: "gpt-4o-mini", label: "GPT-4o mini", tag: "fast" },
  { id: "gpt-4o", label: "GPT-4o" },
];

export function RepoInput({
  onSubmit,
  disabled = false,
  initialPath,
}: RepoInputProps) {
  const { theme, t } = useApp();
  const isDark = theme === "dark";
  const [value, setValue] = useState(initialPath || "");
  const [branch, setBranch] = useState("");
  const [forceRefresh, setForceRefresh] = useState(false);
  const [model, setModel] = useState<"fast" | "thinking">("fast");
  const [customModel, setCustomModel] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [touched, setTouched] = useState(false);
  const inputId = useId();
  const forceId = useId();

  const error = useMemo(() => {
    if (!touched) return null;
    if (!value.trim()) return t.repoInput.errorGithubEmpty;
    if (!GITHUB_URL.test(value.trim())) return t.repoInput.errorGithubInvalid;
    return null;
  }, [touched, value, t]);

  const inputClass = isDark
    ? "border-zinc-700 bg-zinc-950 text-white placeholder:text-zinc-600 focus:border-blue-500"
    : "border-zinc-300 bg-white text-zinc-900 placeholder:text-zinc-400 focus:border-blue-500";

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched(true);
    if (!GITHUB_URL.test(value.trim())) return;
    onSubmit({
      source: "github",
      path: value.trim(),
      branch: branch.trim() || undefined,
      force_refresh: forceRefresh,
      model: customModel.trim() || model,
    });
  };

  return (
    <form
      onSubmit={submit}
      className={`rounded-2xl border p-4 shadow-sm ${isDark ? "border-zinc-800 bg-zinc-900/60" : "border-zinc-200 bg-white"}`}
      noValidate
    >
      <div className="mb-4 flex items-start gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10">
          <Github className="size-4 text-blue-400" />
        </div>
        <div>
          <h2 className="text-sm font-semibold">{t.repoInput.title}</h2>
          <p className={`mt-0.5 text-[11px] leading-relaxed ${isDark ? "text-zinc-500" : "text-zinc-500"}`}>
            {t.repoInput.subtitle}
          </p>
        </div>
      </div>

      <label htmlFor={inputId} className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.12em] text-zinc-500">
        {t.repoInput.labelGithub}
      </label>
      <input
        id={inputId}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onBlur={() => setTouched(true)}
        disabled={disabled}
        placeholder={t.repoInput.placeholderGithub}
        className={`w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:ring-1 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 ${inputClass}`}
      />
      {error && <p className="mt-1.5 text-[11px] font-medium text-red-400">{error}</p>}

      <div className="mt-4">
        <label className="mb-2 block text-[10px] font-bold uppercase tracking-[0.12em] text-zinc-500">{t.repoInput.quickModelLabel}</label>
        <div className="flex gap-3">
          <label className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl border px-3 py-2.5 transition ${model === "fast" ? "border-blue-500 bg-blue-500/10 text-blue-500" : isDark ? "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-800" : "border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100"}`}>
            <input type="radio" className="hidden" name="quick_model" value="fast" checked={model === "fast"} onChange={() => setModel("fast")} disabled={disabled} />
            <span className="text-[11px] font-bold">{t.repoInput.fast}</span>
          </label>
          <label className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl border px-3 py-2.5 transition ${model === "thinking" ? "border-purple-500 bg-purple-500/10 text-purple-500" : isDark ? "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-800" : "border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100"}`}>
            <input type="radio" className="hidden" name="quick_model" value="thinking" checked={model === "thinking"} onChange={() => setModel("thinking")} disabled={disabled} />
            <span className="text-[11px] font-bold">{t.repoInput.thinking}</span>
          </label>
        </div>
      </div>

      <details className={`group mt-3 rounded-xl border ${isDark ? "border-zinc-800 bg-zinc-950/40" : "border-zinc-200 bg-zinc-50"}`}>
        <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-[11px] font-semibold text-zinc-500">
          <SlidersHorizontal className="size-3.5" />
          {t.repoInput.advancedSettings}
          <ChevronDown className="ml-auto size-3.5 transition-transform group-open:rotate-180" />
        </summary>
        <div className={`space-y-3 border-t px-3 py-3 ${isDark ? "border-zinc-800" : "border-zinc-200"}`}>
          <div>
            <label className="mb-1 block text-[10px] font-semibold text-zinc-500">{t.repoInput.branchLabel}</label>
            <input
              value={branch}
              onChange={(event) => setBranch(event.target.value)}
              placeholder={t.repoInput.branchPlaceholder}
              disabled={disabled}
              className={`w-full rounded-lg border px-2.5 py-2 text-xs outline-none ${inputClass}`}
            />
          </div>
          <div className="relative">
            <label className="mb-1 block text-[10px] font-semibold text-zinc-500">{t.repoInput.customModelLabel}</label>
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                disabled={disabled}
                className={`flex w-full items-center justify-between rounded-lg border px-2.5 py-2 text-xs outline-none transition-colors ${inputClass}`}
              >
                <span className="truncate pr-2">
                  {customModel === "" 
                    ? t.repoInput.customModelEmpty 
                    : CUSTOM_MODELS.find(m => m.id === customModel)?.label || customModel}
                </span>
                <ChevronDown className="size-3.5 shrink-0 text-zinc-500" />
              </button>

              {isDropdownOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setIsDropdownOpen(false)} />
                  <div className={`absolute left-0 top-full z-50 mt-1 w-full overflow-hidden rounded-lg border shadow-xl ${isDark ? "border-zinc-700 bg-[#1c1c1c]" : "border-zinc-200 bg-white"}`}>
                    <div className={`px-3 py-2 text-[11px] font-semibold ${isDark ? "text-zinc-500" : "text-zinc-400"}`}>
                      Model
                    </div>
                    <div className="max-h-60 overflow-y-auto pb-1">
                      <button
                        type="button"
                        onClick={() => { setCustomModel(""); setIsDropdownOpen(false); }}
                        className={`flex w-full items-center px-3 py-2 text-left text-xs transition-colors ${customModel === "" ? (isDark ? "bg-zinc-800" : "bg-zinc-100") : ""} ${isDark ? "text-zinc-300 hover:bg-zinc-800" : "text-zinc-700 hover:bg-zinc-100"}`}
                      >
                        {t.repoInput.customModelEmpty}
                      </button>
                      {CUSTOM_MODELS.map((m) => (
                        <button
                          key={m.id}
                          type="button"
                          onClick={() => {
                            if (m.disabled) return;
                            setCustomModel(m.id);
                            setIsDropdownOpen(false);
                          }}
                          className={`flex w-full items-center justify-between px-3 py-2 text-left text-xs transition-colors ${m.disabled ? "cursor-not-allowed opacity-50" : ""} ${customModel === m.id ? (isDark ? "bg-zinc-800/80" : "bg-zinc-100") : ""} ${!m.disabled && (isDark ? "hover:bg-zinc-800/80 text-zinc-300" : "hover:bg-zinc-100 text-zinc-700")}`}
                        >
                          <span className="truncate pr-2">
                            {m.label} {m.disabled && <span className="ml-1 text-[9px] opacity-70">{t.repoInput.comingSoon}</span>}
                          </span>
                          {m.tag === "fast" && (
                            <span className={`flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-medium ${isDark ? "bg-zinc-800 text-zinc-400" : "bg-zinc-200 text-zinc-600"}`}>
                              Fast <Info className="size-3" />
                            </span>
                          )}
                          {m.tag === "thinking" && (
                            <span className={`flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[9px] font-bold ${isDark ? "border-purple-500/20 bg-purple-500/10 text-purple-400" : "border-purple-200 bg-purple-50 text-purple-600"}`}>
                              Thinking <Sparkles className="size-2.5" />
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
          <label htmlFor={forceId} className="flex cursor-pointer items-start gap-2.5">
            <input
              id={forceId}
              type="checkbox"
              checked={forceRefresh}
              onChange={(event) => setForceRefresh(event.target.checked)}
              disabled={disabled}
              className="mt-0.5 size-3.5 rounded border-zinc-600 bg-zinc-900 text-blue-500"
            />
            <span>
              <span className="block text-[11px] font-medium">{t.repoInput.forceRefresh}</span>
              <span className="mt-0.5 block text-[10px] leading-relaxed text-zinc-500">
                {t.repoInput.forceRefreshDesc}
              </span>
            </span>
          </label>
        </div>
      </details>


      <button
        type="submit"
        disabled={disabled}
        className={`mt-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-50 ${isDark ? "bg-white text-black hover:bg-zinc-200" : "bg-zinc-950 text-white hover:bg-zinc-800"}`}
      >
        {disabled && <RefreshCw className="size-3.5 animate-spin" />}
        {disabled ? t.repoInput.submitting : t.repoInput.submit}
      </button>
    </form>
  );
}
