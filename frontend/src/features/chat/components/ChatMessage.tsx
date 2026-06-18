"use client";

import { memo, useState } from "react";
import { motion } from "framer-motion";
import { Bot, User, Copy, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage as ChatMessageType } from "@/features/chat/api/chatApi";
import { useApp } from "@/common/contexts/AppContext";

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

export const ChatMessageBubble = memo(function ChatMessageBubble({
  message,
  isStreaming,
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
          <div className="prose prose-sm prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code: ({ className, children, ...props }) => {
                  const isInline = !className;
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
