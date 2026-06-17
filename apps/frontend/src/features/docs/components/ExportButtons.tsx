export function ExportButtons() {
  return (
    <div className="flex flex-wrap gap-2">
      {["Markdown", "PDF", "Email"].map((label) => (
        <button
          key={label}
          type="button"
          className="rounded-lg border px-3 py-2 text-sm"
          style={{ borderColor: "var(--border-primary)", color: "var(--text-secondary)" }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
