export function GuideViewer() {
  return (
    <article className="rounded-2xl border p-6" style={{ borderColor: "var(--border-primary)" }}>
      <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        GuideViewer
      </p>
      <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
        DOCS-GEN 결과로 생성된 온보딩 가이드와 실행 문서를 표시합니다.
      </p>
    </article>
  );
}
