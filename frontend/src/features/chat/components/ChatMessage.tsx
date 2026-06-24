"use client";

import { memo, useState } from "react";
import { motion } from "framer-motion";
import { Bot, User, Copy, Check, FileCode2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage as ChatMessageType } from "@/features/chat/api/chatApi";
import { useApp } from "@/common/contexts/AppContext";
import { MermaidViewer } from "./MermaidViewer";
import { AgentExplorationTimeline } from "./AgentExplorationTimeline";

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
  onReferenceClick?: (file: string, line: number) => void;
  onSuggestionSelect?: (question: string) => void;
}

export const ChatMessageBubble = memo(function ChatMessageBubble({
  message,
  isStreaming,
  onReferenceClick,
  onSuggestionSelect,
}: ChatMessageProps) {
  const { t } = useApp();
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex gap-3 w-full ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {/* Assistant avatar */}
      {!isUser && (
        <div
          className="flex items-start justify-center w-7 h-7 rounded-lg shrink-0 mt-0.5"
          style={{
            background: "linear-gradient(135deg, var(--accent-purple), var(--accent-blue))",
          }}
        >
          <Bot className="w-4 h-4 text-white mt-1.5" />
        </div>
      )}

      {/* Message bubble */}
      <div
        className={`group relative max-w-[85%] md:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser ? "rounded-br-md" : "rounded-bl-md"
        }`}
        style={{
          background: isUser ? "var(--chat-user-bg)" : "var(--chat-assistant-bg)",
          color: "var(--text-primary)",
          border: isUser ? "none" : "1px solid var(--border-primary)",
        }}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="flex flex-col gap-3">
            {/* Agent Exploration Steps */}
            {message.explorationSteps && message.explorationSteps.length > 0 && (
              <AgentExplorationTimeline 
                steps={message.explorationSteps} 
                isStreaming={isStreaming || false} 
              />
            )}

            <div className="prose prose-sm prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code: ({ className, children, ...props }) => {
                  const match = /language-(\w+)/.exec(className || "");
                  const isInline = !match && !className;
                  const language = match ? match[1] : "";

                  if (language === "mermaid") {
                    const chartText = String(children).replace(/\n$/, "");
                    // 스트리밍 중이거나 내용이 비어있으면 렌더링하지 않고 코드 블록으로 표시
                    if (isStreaming || !chartText || chartText.trim().length < 10) {
                      return (
                        <code
                          className="block overflow-x-auto rounded-lg p-3 text-xs font-mono"
                          style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-primary)" }}
                        >
                          {chartText}
                        </code>
                      );
                    }
                    return <MermaidViewer chart={chartText} />;
                  }

                  if (isInline) {
                    return (
                      <code
                        className="px-1.5 py-0.5 rounded-md text-xs font-mono"
                        style={{
                          background: "var(--bg-secondary)",
                          color: "var(--accent-cyan)",
                        }}
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }
                  return (
                    <code
                      className={`block overflow-x-auto rounded-lg p-3 text-xs font-mono ${className || ""}`}
                      style={{
                        background: "var(--bg-secondary)",
                        border: "1px solid var(--border-primary)",
                      }}
                      {...props}
                    >
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => <pre className="not-prose">{children}</pre>,
              }}
            >
              {message.content}
            </ReactMarkdown>
            {isStreaming && (
              <span
                className="inline-block w-2 h-4 ml-0.5 align-middle"
                style={{
                  background: "var(--accent-blue)",
                  animation: "cursor-blink 1s steps(1) infinite",
                }}
              />
            )}
            </div>

            {message.references && message.references.length > 0 && !isStreaming && (
              <div className="flex flex-wrap gap-1.5 border-t border-zinc-800/70 pt-3">
                {message.references.map((reference) => (
                  <button
                    key={`${reference.file}:${reference.line}`}
                    type="button"
                    onClick={() => onReferenceClick?.(reference.file, reference.line)}
                    className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-950/60 px-2 py-1 font-mono text-[9px] text-zinc-400 transition hover:border-blue-500/40 hover:text-blue-300"
                    title={reference.snippet}
                  >
                    <FileCode2 className="size-3 shrink-0" />
                    <span className="truncate">{reference.file}:{reference.line}</span>
                  </button>
                ))}
              </div>
            )}

            {message.suggestions && message.suggestions.length > 0 && !isStreaming && (
              <div className="flex flex-wrap gap-2 pt-2">
                {message.suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => onSuggestionSelect?.(suggestion)}
                    className="rounded-full border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-[10px] text-zinc-300 transition hover:bg-zinc-800 hover:text-white"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Copy button — assistant messages only */}
        {!isUser && !isStreaming && message.content.length > 0 && (
          <button
            onClick={handleCopy}
            className="absolute -bottom-6 right-0 flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
            style={{
              color: copied ? "var(--accent-green)" : "var(--text-muted)",
              background: "var(--bg-card)",
              border: "1px solid var(--border-primary)",
            }}
          >
            {copied ? (
              <>
                <Check className="w-2.5 h-2.5" />
                {t.chat.copied}
              </>
            ) : (
              <>
                <Copy className="w-2.5 h-2.5" />
                {t.chat.copy}
              </>
            )}
          </button>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div
          className="flex items-center justify-center w-7 h-7 rounded-lg shrink-0 mt-0.5"
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-primary)",
          }}
        >
          <User className="w-4 h-4" style={{ color: "var(--text-muted)" }} />
        </div>
      )}
    </motion.div>
  );
});
