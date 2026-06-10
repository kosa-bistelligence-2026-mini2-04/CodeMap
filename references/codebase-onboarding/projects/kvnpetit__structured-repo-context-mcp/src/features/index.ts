export type * from "@features/types";
export { infoFeature, getServerInfo } from "@features/info";
export { indexCodebaseFeature } from "@features/index-codebase";
export { searchCodeFeature } from "@features/search-code";
export { getIndexStatusFeature } from "@features/get-index-status";
export { getCallGraphFeature } from "@features/get-call-graph";
export { updateIndexFeature } from "@features/update-index";

// Internal features (used by other features, not exposed via CLI/MCP)
export { parseAstFeature } from "@features/parse-ast";
export { queryCodeFeature } from "@features/query-code";
export { listSymbolsFeature } from "@features/list-symbols";
export { analyzeFileFeature } from "@features/analyze-file";

import type { Feature } from "@features/types";
import { getIndexStatusFeature } from "@features/get-index-status";
import { indexCodebaseFeature } from "@features/index-codebase";
import { infoFeature } from "@features/info";
import { searchCodeFeature } from "@features/search-code";
import { updateIndexFeature } from "@features/update-index";

// Registry of features exposed via CLI and MCP
export const features: Feature[] = [
  infoFeature,
  indexCodebaseFeature,
  searchCodeFeature,
  getIndexStatusFeature,
  updateIndexFeature,
];

export function getFeature(name: string): Feature | undefined {
  return features.find((f) => f.name === name);
}
