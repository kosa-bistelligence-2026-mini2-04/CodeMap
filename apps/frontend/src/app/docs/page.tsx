export default function DocsPage() {
  return (
    <main className="min-h-screen px-6 py-24" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>
      <section className="mx-auto flex max-w-5xl flex-col gap-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em]" style={{ color: "var(--text-muted)" }}>
          DOCS-GEN
        </p>
        <h1 className="text-3xl font-bold">가이드북 문서</h1>
        <p className="max-w-2xl text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
          분석 결과로 생성된 온보딩 가이드북을 확인하고 Markdown, PDF, 공유용 산출물로 내보내기 위한 문서 도메인 화면입니다.
        </p>
        <div className="mt-6 rounded-2xl border border-dashed p-8" style={{ borderColor: "var(--border-primary)" }}>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            GuideViewer와 ExportButtons 연결 예정
          </p>
        </div>
      </section>
    </main>
  );
}
