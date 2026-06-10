"use client";

import { AsciiScene } from "@/components/hero/ascii-scene";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

const SUGGESTIONS = [
  {
    repo: "numpy/numpy",
    queryPreview: "How does NumPy decide when a ufunc loop uses SIMD?",
    fullQuery:
      "How does NumPy decide when a ufunc loop uses SIMD, BLAS, or plain C?",
  },
  {
    repo: "cased/kit",
    queryPreview: "How does the Kit code agent dependency analyzer work?",
    fullQuery:
      "How does the dependency analyzer in src/kit/dependency_analyzer work?",
  },
  {
    repo: "pandas-dev/pandas",
    queryPreview: 'When does pandas use "copy-on-write"?',
    fullQuery:
      'When does pandas operate "copy-on-write" vs. view semantics? What code paths trigger real copies during slicing, boolean indexing, and assignment?',
  },
];

export default function Home() {
  const [repoUrl, setRepoUrl] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const trimmedUrl = repoUrl.trim();

    const repoPattern =
      /^(?:https?:\/\/)?(?:www\.)?(?:github\.com\/)?\/?([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+)\/?/i;
    const match = trimmedUrl.match(repoPattern);

    if (!match) {
      setError("Please enter a valid GitHub repository URL or owner/repo");
      setLoading(false);
      return;
    }

    const [, owner, repo] = match;

    const cleanRepo = repo.split(/[\/?#]/)[0];

    if (!owner || !cleanRepo) {
      setError("Please enter a valid GitHub repository URL or owner/repo");
      setLoading(false);
      return;
    }

    router.push(`/${owner}/${cleanRepo}`);
  };

  return (
    <div className="relative flex flex-col items-center justify-center min-h-screen bg-neutral-50 px-4 overflow-hidden">
      <AsciiScene />

      <div className="relative z-10 w-full max-w-sm">
        <div className="text-left mb-4">
          <h1 className="font-display text-2xl md:text-3xl font-medium tracking-tight mb-2 text-neutral-900 select-none">
            Chat with Code
          </h1>
          <p className="text-zinc-600 select-none">
            Chunk and embed any Github repository.
            <br />
            Entirely within your browser.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="w-full relative group">
          <div className="relative flex items-center">
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/chroma-core/chroma"
              className="w-full px-4 py-4 text-base md:text-sm border-input placeholder:text-muted-foreground focus-visible:border-ring border rounded-lg outline-none bg-secondary pr-12 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !repoUrl.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-zinc-800 text-white hover:bg-zinc-700 disabled:bg-zinc-300 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
            </button>
          </div>
        </form>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="ml-2 mt-2 text-red-500 text-xs font-medium"
          >
            {error}
          </motion.p>
        )}
        <div className="flex flex-col gap-1 ml-2 mt-4">
          {SUGGESTIONS.map((suggestion, index) => (
            <motion.a
              key={suggestion.repo}
              href={`/${suggestion.repo}?q=${encodeURIComponent(suggestion.fullQuery)}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.4,
                delay: index * 0.05,
                ease: "easeOut",
              }}
              className="text-zinc-500 hover:underline text-xs"
            >
              {suggestion.queryPreview}{" "}
              <ArrowRight className="w-3 h-3 inline-block" />
            </motion.a>
          ))}
        </div>
      </div>

      <div className="absolute bottom-8 text-center text-sm text-neutral-500 z-10">
        Built using{" "}
        <a
          href="https://trychroma.com"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-neutral-800 transition-colors"
        >
          Chroma
        </a>{" "}
        and{" "}
        <a
          href="https://ai-sdk.dev"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-neutral-800 transition-colors"
        >
          Vercel AI SDK
        </a>
      </div>
    </div>
  );
}
