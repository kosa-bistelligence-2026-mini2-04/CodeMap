"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Trash2, MessageSquare } from "lucide-react";
import { useApp } from "@/common/contexts/AppContext";
import { ModeSelector } from "./ModeSelector";
import { SuggestionChips } from "./SuggestionChips";
import { ChatMessageBubble } from "./ChatMessage";
import { StreamingStatus } from "./StreamingStatus";
import {
  streamChat,
  simulateStream,
  type ChatMessage,
  type ChatMode,
  type StreamPhase,
} from "@/features/chat/api/chatApi";

export function ChatInterface() {
  const { t } = useApp();
  const searchParams = useSearchParams();
  const repoId = searchParams.get("repo_id") || "";

  // State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<ChatMode>("lite");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamPhase, setStreamPhase] = useState<StreamPhase | null>(null);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamPhase]);

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  };

  // Send message
  const handleSend = useCallback(
    async (text?: string) => {
      const msg = (text || input).trim();
      if (!msg || isStreaming) return;

      // Add user message
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: msg,
        timestamp: Date.now(),
        mode,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsStreaming(true);
      setStreamPhase(null);

      // Reset textarea height
      if (inputRef.current) {
        inputRef.current.style.height = "auto";
      }

      // Create assistant message placeholder
      const assistantId = crypto.randomUUID();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: Date.now(),
        mode,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      try {
        // Decide which stream to use
        const stream = repoId
          ? streamChat(repoId, msg, mode)
          : simulateStream(msg, mode);

        for await (const event of stream) {
          switch (event.type) {
            case "status":
              if (event.phase) setStreamPhase(event.phase);
              break;
            case "content":
              if (event.content) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: m.content + event.content }
                      : m,
                  ),
                );
              }
              break;
            case "done":
              setStreamPhase("complete");
              break;
            case "error":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content: `⚠️ ${event.error || "An error occurred."}`,
                      }
                    : m,
                ),
              );
              break;
          }
        }
      } catch {
        // Handle unexpected errors
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: "⚠️ Unexpected error occurred." }
              : m,
          ),
        );
      } finally {
        setIsStreaming(false);
        setTimeout(() => setStreamPhase(null), 1500);
      }
    },
    [input, isStreaming, mode, repoId],
  );

  // Keyboard handler
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Clear conversation
  const handleClear = () => {
    if (isStreaming) return;
    setMessages([]);
    setStreamPhase(null);
  };

  const isEmpty = messages.length === 0;

  return (
    <main
      className="flex flex-col h-[calc(100vh-3.5rem)]"
      style={{ background: "var(--bg-primary)" }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 md:px-6 py-3 border-b shrink-0"
        style={{ borderColor: "var(--border-primary)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex items-center gap-2"
            style={{ color: "var(--text-primary)" }}
          >
            <MessageSquare className="w-4 h-4" style={{ color: "var(--accent-blue)" }} />
            <h1 className="text-sm font-bold">{t.chat.title}</h1>
          </div>
          {repoId && (
            <span
              className="px-2 py-0.5 rounded-md text-[10px] font-mono"
              style={{
                background: "var(--bg-secondary)",
                color: "var(--text-muted)",
                border: "1px solid var(--border-primary)",
              }}
            >
              {repoId}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <ModeSelector mode={mode} onChange={setMode} disabled={isStreaming} />
          <button
            onClick={handleClear}
            disabled={isEmpty || isStreaming}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
            style={{ color: "var(--text-muted)" }}
            title={t.chat.clear}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4">
        <div className="mx-auto max-w-3xl flex flex-col gap-6">
          <AnimatePresence mode="wait">
            {isEmpty ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <SuggestionChips onSelect={(q) => handleSend(q)} />
              </motion.div>
            ) : (
              <motion.div
                key="messages"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col gap-6"
              >
                {messages.map((msg, i) => (
                  <ChatMessageBubble
                    key={msg.id}
                    message={msg}
                    isStreaming={
                      isStreaming &&
                      msg.role === "assistant" &&
                      i === messages.length - 1
                    }
                  />
                ))}

                {/* Streaming status indicator */}
                {isStreaming && streamPhase && streamPhase !== "complete" && (
                  <div className="pl-10">
                    <StreamingStatus phase={streamPhase} />
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div
        className="shrink-0 border-t px-4 md:px-6 py-3"
        style={{ borderColor: "var(--border-primary)" }}
      >
        <div className="mx-auto max-w-3xl flex items-end gap-2">
          <div
            className="flex-1 rounded-xl overflow-hidden"
            style={{
              background: "var(--bg-input)",
              border: "1px solid var(--border-input)",
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={t.chat.placeholder}
              disabled={isStreaming}
              rows={1}
              className="w-full resize-none bg-transparent px-4 py-3 text-sm outline-none disabled:opacity-50"
              style={{
                color: "var(--text-primary)",
                maxHeight: "160px",
              }}
            />
          </div>
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isStreaming}
            className="flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-150 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
            style={{
              background: input.trim() && !isStreaming ? "var(--accent-blue)" : "var(--bg-secondary)",
              color: input.trim() && !isStreaming ? "#ffffff" : "var(--text-faint)",
            }}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p
          className="text-center mt-2 text-[10px]"
          style={{ color: "var(--text-faint)" }}
        >
          {t.chat.disclaimer}
        </p>
      </div>
    </main>
  );
}
