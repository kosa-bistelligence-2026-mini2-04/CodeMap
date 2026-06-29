import type {
  ParseDetails,
  WorkspaceFile,
  WorkspaceReport,
} from "@/common/types/contracts";

function fileName(path: string): string {
  return path.split("/").filter(Boolean).at(-1) || path;
}

export function mergeParseDetails(
  report: WorkspaceReport,
  details: ParseDetails,
): WorkspaceReport {
  const fileMap = details.codemap.fileMap;
  const parseFiles: WorkspaceFile[] = fileMap.map((item) => ({
    path: item.path,
    name: fileName(item.path),
    language: item.language || "Unknown",
    lines: item.lines || 0,
    bytes: item.bytes || 0,
    kind: /test|spec/.test(item.path.toLowerCase()) ? "test" : "source",
  }));
  const riskFiles = [...details.codemap.heatmap]
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map((item) => `${item.path} risk score ${item.score}`);
  const entrypointPaths = details.tree.entryPoints.map((item) => item.path);

  return {
    ...report,
    stack: details.stack.techStack.map((item) => item.name),
    entrypoints: entrypointPaths,
    files: parseFiles.length > 0 ? parseFiles : report.files,
    executive_summary:
      details.summary.projectSummary ||
      details.readme.projectPurpose ||
      report.executive_summary,
    reading_order: entrypointPaths.length > 0 ? entrypointPaths : report.reading_order,
    key_risks: riskFiles.length > 0 ? riskFiles : report.key_risks,
  };
}
