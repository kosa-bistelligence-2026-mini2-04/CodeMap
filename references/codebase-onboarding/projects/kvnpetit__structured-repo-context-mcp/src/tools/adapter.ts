import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { Feature } from "@features/types";
import { z } from "zod";

function zodToMcpSchema(schema: z.ZodType): Record<string, z.ZodType> {
  if (schema instanceof z.ZodObject) {
    return schema.shape as Record<string, z.ZodType>;
  }
  return { input: schema };
}

export function registerFeatureAsTool(
  server: McpServer,
  feature: Feature,
): void {
  const mcpSchema = zodToMcpSchema(feature.schema);

  // eslint-disable-next-line @typescript-eslint/no-deprecated
  server.tool(feature.name, feature.description, mcpSchema, async (params) => {
    const result = feature.execute(params);

    const formatResult = (
      res: Awaited<ReturnType<typeof feature.execute>>,
    ): {
      content: { type: "text"; text: string }[];
      isError: boolean;
    } => ({
      content: [
        {
          type: "text" as const,
          text: res.message ?? JSON.stringify(res.data, null, 2),
        },
      ],
      isError: !res.success,
    });

    if (result instanceof Promise) {
      return await result.then(formatResult);
    }
    return formatResult(result);
  });
}
