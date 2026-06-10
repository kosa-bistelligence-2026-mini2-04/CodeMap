import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { features } from "@features";
import { registerFeatureAsTool } from "@tools/adapter";

export function registerTools(server: McpServer): void {
  for (const feature of features) {
    registerFeatureAsTool(server, feature);
  }
}

export { features as tools };
