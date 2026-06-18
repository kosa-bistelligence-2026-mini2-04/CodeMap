"use client";

import {
  ArrowRight,
  Check,
  FolderOpen,
  Github,
  LoaderCircle,
  Search,
  Star,
} from "lucide-react";
import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useApp } from "@/common/contexts/AppContext";
import { apiPath } from "@/features/analysis/api/api";
import { useRouter } from "next/navigation";

type SourceMode = "github" | "local";

type RepositorySuggestion = {
  id: number;
  name: string;
  fullName: string;
  url: string;
  description: string | null;
  language: string | null;
  stars: number;
  ownerAvatar: string;
};

type RepositoryLauncherProps = {
  onAnalyze: (url: string) => void;
};

type LocalFolderSelection = {
  name: string;
  files: File[];
  paths: string[];
  skippedCount: number;
};

const GITHUB_URL = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+?(?:\.git)?\/?$/;
const MAX_LOCAL_FILES = 900;
const MAX_LOCAL_FILE_BYTES = 5 * 1024 * 1024;
const MAX_LOCAL_UPLOAD_BYTES = 50 * 1024 * 1024;
const IGNORED_DIRECTORIES = new Set([
  ".git", ".next", ".nuxt", ".pytest_cache", ".tox", ".venv", "__pycache__",
  "build", "coverage", "dist", "node_modules", "out", "target", "venv",
]);
const IGNORED_FILES = new Set([".env", ".env.development", ".env.local", ".env.production", ".env.test", ".npmrc", ".pypirc"]);

function formatStars(stars: number): string {
  if (stars >= 1_000_000) return `${(stars / 1_000_000).toFixed(1)}m`;
  if (stars >= 1_000) return `${(stars / 1_000).toFixed(stars >= 100_000 ? 0 : 1)}k`;
  return String(stars);
}

export function RepositoryLauncher({ onAnalyze }: RepositoryLauncherProps) {
  const { t } = useApp();
  const router = useRouter();
  const [mode, setMode] = useState<SourceMode>("github");
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<RepositorySuggestion[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [formError, setFormError] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [selectedFolder, setSelectedFolder] = useState<LocalFolderSelection | null>(null);
  const [localUploading, setLocalUploading] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const listId = useId();

  useEffect(() => {
    const input = folderInputRef.current;
    if (!input) return;
    input.setAttribute("webkitdirectory", "");
    input.setAttribute("directory", "");
  }, []);

  useEffect(() => {
    const trimmed = query.trim();
    if (mode !== "github" || trimmed.length < 2 || GITHUB_URL.test(trimmed)) {
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setSearching(true);
      setSearchError("");
      try {
        const response = await fetch(`${apiPath("/github/repositories")}?q=${encodeURIComponent(trimmed)}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("search_failed");
        const data = (await response.json()) as { items?: RepositorySuggestion[] };
        setSuggestions(data.items || []);
        setHighlightedIndex(data.items?.length ? 0 : -1);
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setSuggestions([]);
          setSearchError(t.hero.searchError);
        }
      } finally {
        if (!controller.signal.aborted) setSearching(false);
      }
    }, 320);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [mode, query, t.hero.searchError]);

  const selectSuggestion = (repo: RepositorySuggestion) => {
    setQuery(repo.url);
    setSuggestions([]);
    setHighlightedIndex(-1);
    setFormError("");
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (mode === "local") return;

    const trimmed = query.trim();
    if (GITHUB_URL.test(trimmed)) {
      onAnalyze(trimmed);
      return;
    }
    if (suggestions.length > 0) {
      onAnalyze(suggestions[Math.max(0, highlightedIndex)].url);
      return;
    }
    setFormError(t.hero.searchPrompt);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!suggestions.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlightedIndex((index) => (index + 1) % suggestions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightedIndex((index) => (index <= 0 ? suggestions.length - 1 : index - 1));
    } else if (event.key === "Escape") {
      setSuggestions([]);
      setHighlightedIndex(-1);
    }
  };

  const handleFolderChange = () => {
    const selectedFiles = Array.from(folderInputRef.current?.files || []);
    if (!selectedFiles.length) return;
    const relativePath = selectedFiles[0].webkitRelativePath || selectedFiles[0].name;
    const folderName = relativePath.split("/")[0];
    const files: File[] = [];
    const paths: string[] = [];
    let totalBytes = 0;
    let skippedCount = 0;

    for (const file of selectedFiles) {
      const rawPath = file.webkitRelativePath || file.name;
      const parts = rawPath.split("/").filter(Boolean);
      const repositoryPath = parts[0] === folderName ? parts.slice(1) : parts;
      const filename = repositoryPath.at(-1) || file.name;
      const ignored = repositoryPath.slice(0, -1).some((part) => IGNORED_DIRECTORIES.has(part))
        || IGNORED_FILES.has(filename)
        || (filename.startsWith(".env.") && filename !== ".env.example")
        || file.size > MAX_LOCAL_FILE_BYTES
        || files.length >= MAX_LOCAL_FILES
        || totalBytes + file.size > MAX_LOCAL_UPLOAD_BYTES;
      if (ignored) {
        skippedCount += 1;
        continue;
      }
      files.push(file);
      paths.push(repositoryPath.join("/"));
      totalBytes += file.size;
    }

    if (!files.length) {
      setSelectedFolder(null);
      setFormError(t.hero.localEmptyError);
      return;
    }
    setSelectedFolder({
      name: folderName,
      files,
      paths,
      skippedCount,
    });
    setFormError("");
  };

  const submitLocalFolder = async () => {
    if (!selectedFolder || localUploading) return;
    setLocalUploading(true);
    setFormError("");
    const body = new FormData();
    body.append("folderName", selectedFolder.name);
    body.append("model", "auto");
    selectedFolder.files.forEach((file, index) => {
      body.append("files", file, file.name);
      body.append("paths", selectedFolder.paths[index]);
    });

    try {
      const response = await fetch(apiPath("/repo/analysis/local"), { method: "POST", body });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.message || t.hero.localUploadError);
      router.push(`/analyze?job=${encodeURIComponent(payload.data.jobId)}`);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : t.hero.localUploadError);
      setLocalUploading(false);
    }
  };

  const showSuggestions = mode === "github" && isFocused && query.trim().length >= 2 && !GITHUB_URL.test(query.trim());

  return (
    <div className="w-full max-w-2xl mt-3">
      <div className="mx-auto mb-3 flex w-fit rounded-xl border p-1 cm-card" role="tablist" aria-label={t.hero.sourceLabel}>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "github"}
          onClick={() => { setMode("github"); setSuggestions([]); setSearchError(""); setFormError(""); }}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition ${mode === "github" ? "bg-blue-500 text-white shadow-sm" : "cm-text-muted hover:cm-text-primary"}`}
        >
          <Github className="size-3.5" /> {t.hero.sourceGithub}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "local"}
          onClick={() => { setMode("local"); setSuggestions([]); setSearchError(""); setFormError(""); }}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition ${mode === "local" ? "bg-blue-500 text-white shadow-sm" : "cm-text-muted hover:cm-text-primary"}`}
        >
          <FolderOpen className="size-3.5" /> {t.hero.sourceLocal}
        </button>
      </div>

      {mode === "github" ? (
        <form onSubmit={submit} className="relative w-full">
          <div className="group relative flex items-center">
            <div className="absolute left-4 z-10 cm-text-faint">
              {searching ? <LoaderCircle className="size-4 animate-spin" /> : <Search className="size-4" />}
            </div>
            <input
              type="text"
              value={query}
              onChange={(event) => { setQuery(event.target.value); setSuggestions([]); setSearching(false); setSearchError(""); setHighlightedIndex(-1); setFormError(""); }}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => window.setTimeout(() => setIsFocused(false), 150)}
              placeholder={t.hero.placeholder}
              className="w-full rounded-2xl py-4 pl-11 pr-14 text-sm shadow-lg transition-all cm-input"
              role="combobox"
              aria-autocomplete="list"
              aria-expanded={showSuggestions}
              aria-controls={listId}
              aria-activedescendant={highlightedIndex >= 0 ? `${listId}-${highlightedIndex}` : undefined}
            />
            <button
              type="submit"
              disabled={!query.trim() || searching}
              className="absolute right-2 top-1/2 -translate-y-1/2 cursor-pointer rounded-xl p-2.5 shadow-sm transition-all disabled:cursor-not-allowed cm-btn-primary"
              aria-label={t.hero.submit}
            >
              <ArrowRight className="size-4" />
            </button>
          </div>

          {showSuggestions && (
            <div id={listId} role="listbox" className="absolute left-0 right-0 top-full z-30 mt-2 overflow-hidden rounded-2xl border shadow-2xl cm-card">
              {searchError ? (
                <p className="px-4 py-3 text-left text-xs text-red-400">{searchError}</p>
              ) : searching && !suggestions.length ? (
                <p className="px-4 py-3 text-left text-xs cm-text-muted">{t.hero.searching}</p>
              ) : suggestions.length ? (
                suggestions.map((repo, index) => (
                  <button
                    id={`${listId}-${index}`}
                    key={repo.id}
                    type="button"
                    role="option"
                    aria-selected={highlightedIndex === index}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectSuggestion(repo)}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    className={`flex w-full items-center gap-3 border-b px-4 py-3 text-left last:border-0 ${highlightedIndex === index ? "bg-blue-500/10" : "hover:bg-blue-500/5"}`}
                    style={{ borderColor: "var(--border-primary)" }}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={repo.ownerAvatar} alt="" className="size-8 rounded-lg bg-zinc-800" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-bold cm-text-primary">{repo.fullName}</span>
                      <span className="mt-0.5 block truncate text-[10px] cm-text-faint">{repo.description || t.hero.noDescription}</span>
                    </span>
                    <span className="flex shrink-0 items-center gap-1 text-[10px] cm-text-faint">
                      <Star className="size-3" /> {formatStars(repo.stars)}
                    </span>
                  </button>
                ))
              ) : !searching ? (
                <p className="px-4 py-3 text-left text-xs cm-text-muted">{t.hero.noResults}</p>
              ) : null}
            </div>
          )}
        </form>
      ) : (
        <div className="rounded-2xl border p-3 shadow-lg cm-card">
          <input ref={folderInputRef} type="file" multiple className="hidden" onChange={handleFolderChange} />
          <button
            type="button"
            onClick={() => folderInputRef.current?.click()}
            className="flex w-full items-center gap-3 rounded-xl border border-dashed px-4 py-4 text-left transition hover:border-blue-500/50 hover:bg-blue-500/5"
            style={{ borderColor: selectedFolder ? "var(--accent-blue)" : "var(--border-input)" }}
          >
            <span className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${selectedFolder ? "bg-emerald-500/10 text-emerald-400" : "bg-blue-500/10 text-blue-400"}`}>
              {selectedFolder ? <Check className="size-5" /> : <FolderOpen className="size-5" />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-bold cm-text-primary">
                {selectedFolder?.name || t.hero.chooseFolder}
              </span>
              <span className="mt-1 block text-[11px] leading-4 cm-text-muted">
                {selectedFolder
                  ? t.hero.folderSelected
                      .replace("{count}", String(selectedFolder.files.length))
                      .replace("{skipped}", String(selectedFolder.skippedCount))
                  : t.hero.folderPickerHint}
              </span>
            </span>
            <span className="shrink-0 rounded-lg border px-2.5 py-1.5 text-[10px] font-bold cm-text-muted" style={{ borderColor: "var(--border-primary)" }}>
              {selectedFolder ? t.hero.chooseAgain : t.hero.browse}
            </span>
          </button>
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-500/10 px-3 py-2.5 text-left text-[10px] leading-4 text-amber-500">
            <span className="mt-1 size-1.5 shrink-0 rounded-full bg-amber-400" />
            <p>{t.hero.localBridgeNotice}</p>
          </div>
          <button
            type="button"
            disabled={!selectedFolder || localUploading}
            onClick={submitLocalFolder}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-xs font-bold disabled:cursor-not-allowed disabled:opacity-40 cm-btn-primary"
          >
            {localUploading && <LoaderCircle className="size-3.5 animate-spin" />}
            {localUploading ? t.hero.localUploading : t.hero.localAnalyze}
          </button>
        </div>
      )}

      {(formError || searchError) && !showSuggestions && (
        <p className="mt-2 ml-1 text-left text-xs font-semibold text-red-400">{formError || searchError}</p>
      )}
      {mode === "github" && <p className="mt-3 text-center text-[10px] cm-text-faint">{t.hero.searchHint}</p>}
    </div>
  );
}
