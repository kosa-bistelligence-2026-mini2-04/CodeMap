import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { config } from "@config";
import { registerTools } from "@tools";
import { registerResources } from "@resources";
import { registerPrompts } from "@prompts";
import { logger } from "@utils";

export function createServer(): McpServer {
  const server = new McpServer({
    name: config.name,
    version: config.version,
  });

  registerTools(server);
  registerResources(server);
  registerPrompts(server);

  return server;
}

export async function startServer(): Promise<void> {
  const server = createServer();
  const transport = new StdioServerTransport();

  await server.connect(transport);
  logger.info(`${config.name} v${config.version} started`);
}
