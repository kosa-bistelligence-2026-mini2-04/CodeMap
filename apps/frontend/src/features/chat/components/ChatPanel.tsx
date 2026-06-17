export function ChatPanel() {
  return (
    <section className="rounded-2xl border border-dashed p-6" style={{ borderColor: "var(--border-primary)" }}>
      <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        ChatPanel
      </p>
      <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
        AGENT-CHAT API 연결 후 사용자 질문과 AI 응답을 표시합니다.
      </p>
    </section>
  );
}
