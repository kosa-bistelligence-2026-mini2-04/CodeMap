"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Editor, type OnMount } from "@monaco-editor/react";
import type { editor as MonacoEditor } from "monaco-editor";
import { Check, Copy, FileCode2, Loader2, TriangleAlert, X } from "lucide-react";
import { fetchFileContent } from "@/features/analysis/api/api";
import { extractSymbols } from "@/features/analysis/utils/extractSymbols";
import { SymbolsPanel } from "@/features/analysis/components/SymbolsPanel";
import { useApp } from "@/common/contexts/AppContext";


interface CodeNavigatorPanelProps {
  jobId: string;
  filePath: string;
  highlightLine?: number | null;
  highlightLineEnd?: number | null;
  onClose: () => void;
}

type LoadState = "idle" | "loading" | "success" | "error";

// API 언어값 → Monaco language id 매핑
const MONACO_LANG: Record<string, string> = {
  python: "python",
  typescript: "typescript",
  tsx: "typescript",
  javascript: "javascript",
  jsx: "javascript",
  json: "json",
  html: "html",
  css: "css",
  scss: "scss",
  markdown: "markdown",
  go: "go",
  java: "java",
  kotlin: "kotlin",
  rust: "rust",
  cpp: "cpp",
  c: "c",
  csharp: "csharp",
  ruby: "ruby",
  php: "php",
  sql: "sql",
  yaml: "yaml",
  xml: "xml",
  bash: "shell",
};

function monacoLanguage(language: string | null): string {
  if (!language) return "plaintext";
  return MONACO_LANG[language.toLowerCase()] ?? "plaintext";
}


export function CodeNavigatorPanel({
  jobId,
  filePath,
  highlightLine,
  highlightLineEnd,
  onClose,
}: CodeNavigatorPanelProps) {
  const { theme } = useApp();
  const isDark = theme === "dark";

  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [content, setContent] = useState("");
  const [language, setLanguage] = useState<string | null>(null);
  const [lines, setLines] = useState(0);
  const [truncated, setTruncated] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [copied, setCopied] = useState(false);
  const [activeLine, setActiveLine] = useState<number | null>(null);
  const [mounted, setMounted] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  // monaco 인스턴스(Range 등 사용). @monaco-editor/react onMount 2번째 인자.
  const monacoRef = useRef<typeof import("monaco-editor") | null>(null);
  const decorationsRef = useRef<string[]>([]);

  const symbols = useMemo(() => extractSymbols(content, language), [content, language]);

  // 파일 내용 로드
  useEffect(() => {
    if (!filePath) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoadState("loading");
    setContent("");
    setErrorMsg("");
    setCopied(false);
    setActiveLine(highlightLine ?? null);

    fetchFileContent(jobId, filePath, controller.signal)
      .then((res) => {
        setContent(res.data.content);
        setLanguage(res.data.language);
        setLines(res.data.lines);
        setTruncated(res.data.truncated);
        setLoadState("success");
      })
      .catch((err: Error) => {
        if (err.name === "AbortError") return;
        setErrorMsg(err.message);
        setLoadState("error");
      });

    return () => {
      controller.abort();
    };
    // highlightLine 변경만으로 재요청하지 않도록 의도적으로 제외
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, filePath]);

  // 외부(채팅 근거 등)에서 전달된 highlightLine을 반영
  useEffect(() => {
    setActiveLine(highlightLine ?? null);
  }, [highlightLine]);

  // 에디터에 라인 점프 + 하이라이트 적용 (revealLine + deltaDecorations)
  useEffect(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco || loadState !== "success") return;

    if (!activeLine) {
      decorationsRef.current = editor.deltaDecorations(decorationsRef.current, []);
      return;
    }

    const endLine = highlightLineEnd && highlightLineEnd >= activeLine ? highlightLineEnd : activeLine;
    editor.revealLineInCenter(activeLine);
    editor.setPosition({ lineNumber: activeLine, column: 1 });
    decorationsRef.current = editor.deltaDecorations(decorationsRef.current, [
      {
        range: new monaco.Range(activeLine, 1, endLine, 1),
        options: {
          isWholeLine: true,
          className: "codemap-symbol-line",
          linesDecorationsClassName: "codemap-symbol-gutter",
        },
      },
    ]);
  }, [activeLine, highlightLineEnd, loadState, mounted]);

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco as unknown as typeof import("monaco-editor");
    setMounted(true);
  };

  const handleSymbolSelect = (line: number) => {
    setActiveLine(line);
    // 이미 같은 라인이라도 재점프되도록 직접 호출
    editorRef.current?.revealLineInCenter(line);
  };

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const fileName = filePath.split("/").at(-1) ?? filePath;

  return (
    <div
      className={`flex h-full flex-col overflow-hidden border-l ${
        isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-white"
      }`}
    >
      {/* Monaco 데코레이션용 전역 스타일 */}
      <style>{`
        .codemap-symbol-line { background: rgba(250, 204, 21, 0.16); }
        .codemap-symbol-gutter { background: rgba(250, 204, 21, 0.75); width: 3px !important; margin-left: 3px; }
      `}</style>

      {/* 헤더 */}
      <div
        className={`flex shrink-0 items-center gap-2 border-b px-3 py-2 ${
          isDark ? "border-zinc-800" : "border-zinc-200"
        }`}
      >
        <FileCode2 className="size-3.5 shrink-0 text-zinc-500" />
        <span
          className={`min-w-0 flex-1 truncate font-mono text-[11px] font-semibold ${
            isDark ? "text-zinc-200" : "text-zinc-800"
          }`}
          title={filePath}
        >
          {fileName}
        </span>
        {loadState === "success" && (
          <span className="shrink-0 text-[9px] text-zinc-500">
            {language ?? "text"} · {lines.toLocaleString()} lines
          </span>
        )}
        {activeLine && (
          <span className="shrink-0 rounded bg-blue-500/10 px-1.5 py-0.5 font-mono text-[9px] font-bold text-blue-400">
            L{activeLine}
            {highlightLineEnd && highlightLineEnd !== activeLine ? `-${highlightLineEnd}` : ""}
          </span>
        )}
        <button
          type="button"
          onClick={handleCopy}
          disabled={loadState !== "success"}
          title="클립보드에 복사"
          aria-label="클립보드에 복사"
          className={`flex size-6 items-center justify-center rounded transition disabled:opacity-30 ${
            isDark ? "text-zinc-500 hover:bg-zinc-800 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
          }`}
        >
          {copied ? <Check className="size-3.5 text-emerald-400" /> : <Copy className="size-3.5" />}
        </button>
        <button
          type="button"
          onClick={onClose}
          title="닫기"
          aria-label="코드 내비게이터 닫기"
          className={`flex size-6 items-center justify-center rounded transition ${
            isDark ? "text-zinc-500 hover:bg-zinc-800 hover:text-white" : "text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
          }`}
        >
          <X className="size-3.5" />
        </button>
      </div>

      {/* 경로 표시 */}
      <div
        className={`shrink-0 truncate px-3 py-1 font-mono text-[9px] ${
          isDark ? "text-zinc-600" : "text-zinc-400"
        }`}
        title={filePath}
      >
        {filePath}
      </div>

      {/* 본문: 좌측 Monaco 뷰어 + 우측 Symbols 패널 */}
      <div className="flex min-h-0 flex-1">
        <div className="relative min-w-0 flex-1">
          {loadState === "loading" && (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="size-5 text-zinc-500 motion-safe:animate-spin" />
            </div>
          )}

          {loadState === "error" && (
            <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
              <TriangleAlert className="size-5 text-red-400" />
              <p className="text-xs text-zinc-500">{errorMsg}</p>
            </div>
          )}

          {loadState === "success" && (
            <>
              {truncated && (
                <div
                  className={`absolute inset-x-0 top-0 z-10 px-3 py-1.5 text-[10px] font-medium ${
                    isDark ? "bg-yellow-500/10 text-yellow-400" : "bg-yellow-50 text-yellow-700"
                  }`}
                >
                  파일이 너무 커서 처음 50,000자만 표시됩니다.
                </div>
              )}
              <Editor
                height="100%"
                theme={isDark ? "vs-dark" : "light"}
                language={monacoLanguage(language)}
                value={content}
                onMount={handleEditorMount}
                loading={<Loader2 className="size-5 text-zinc-500 motion-safe:animate-spin" />}
                options={{
                  readOnly: true,
                  domReadOnly: true,
                  minimap: { enabled: false },
                  fontSize: 12,
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  renderLineHighlight: "all",
                  automaticLayout: true,
                  wordWrap: "on",
                  contextmenu: false,
                }}
              />
            </>
          )}
        </div>

        {loadState === "success" && (
          <SymbolsPanel
            symbols={symbols}
            activeLine={activeLine}
            onSelect={handleSymbolSelect}
            isDark={isDark}
          />
        )}
      </div>
    </div>
  );
}
