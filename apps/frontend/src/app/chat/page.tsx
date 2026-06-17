export default function ChatPage() {
  return (
    <main className="min-h-screen px-6 py-24" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>
      <section className="mx-auto flex max-w-5xl flex-col gap-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: "var(--text-muted)" }}>
          AGENT-CHAT
        </p>
        <h1 className="text-3xl font-bold">AI 자율 탐색 및 채팅</h1>
        <p className="max-w-2xl text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
          저장소 분석 결과를 바탕으로 사용자 질문에 답변하고, 필요한 경우 추가 탐색을 수행하는 채팅 도메인 화면입니다.
        </p>
        <div className="mt-6 rounded-2xl border border-dashed p-8" style={{ borderColor: "var(--border-primary)" }}>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            ChatPanel 연결 예정
          </p>
        </div>
      </section>
    </main>
  );
}
