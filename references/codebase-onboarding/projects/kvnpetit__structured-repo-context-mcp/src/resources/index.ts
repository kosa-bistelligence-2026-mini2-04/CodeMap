import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { getServerInfo } from "@features";

export function registerResources(server: McpServer): void {
  // eslint-disable-next-line @typescript-eslint/no-deprecated
  server.resource("server_info", "src://server/info", (uri) => {
    const info = getServerInfo();
    return {
      contents: [
        {
          uri: uri.href,
          mimeType: "application/json",
          text: JSON.stringify(info, null, 2),
        },
      ],
    };
  });
}
