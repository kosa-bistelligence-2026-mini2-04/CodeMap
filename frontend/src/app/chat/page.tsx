"use client";

import { Suspense } from "react";
import { ChatInterface } from "@/features/chat/components/ChatInterface";

function ChatContent() {
  return <ChatInterface />;
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div
          className="flex items-center justify-center min-h-[calc(100vh-3.5rem)]"
          style={{ background: "var(--bg-primary)" }}
        >
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Loading...
          </p>
        </div>
      }
    >
      <ChatContent />
    </Suspense>
  );
}
