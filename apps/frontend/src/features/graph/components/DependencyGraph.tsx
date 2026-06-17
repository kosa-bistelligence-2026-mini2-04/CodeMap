export function DependencyGraph() {
  return (
    <section className="rounded-2xl border border-dashed p-6" style={{ borderColor: "var(--border-primary)" }}>
      <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        DependencyGraph
      </p>
      <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
        RAG-GRAPH 결과를 바탕으로 파일과 모듈 간 의존성 관계를 시각화합니다.
      </p>
    </section>
  );
}
