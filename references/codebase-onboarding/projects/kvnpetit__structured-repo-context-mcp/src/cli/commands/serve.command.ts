import { defineCommand } from "citty";
import { startServer } from "@/server";
import { createIndexWatcher } from "@core/embeddings";
import { EMBEDDING_CONFIG } from "@config";
import { logger } from "@utils";

export const serveCommand = defineCommand({
  meta: {
    name: "serve",
    description: "Start the MCP server",
  },
  args: {
    transport: {
      type: "string",
      alias: "t",
      description: "Transport type (stdio)",
      default: "stdio",
    },
    directory: {
      type: "string",
      alias: "d",
      description:
        "Directory to watch and index (defaults to current directory)",
      default: ".",
    },
    watch: {
      type: "boolean",
      alias: "w",
      description: "Enable file watcher for automatic indexing",
      default: true,
    },
  },
  async run({ args }) {
    const { directory, watch } = args;

    // Start watcher if enabled
    if (watch) {
      const watcher = createIndexWatcher({
        directory,
        config: EMBEDDING_CONFIG,
        onError: (error) => {
          logger.error(`Watcher error: ${error.message}`);
        },
      });

      try {
        await watcher.start();
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        logger.warn(`Watcher disabled: ${msg}`);
      }

      // Cleanup on exit
      process.on("SIGINT", () => {
        void watcher.stop();
        process.exit(0);
      });
      process.on("SIGTERM", () => {
        void watcher.stop();
        process.exit(0);
      });
    }

    await startServer();
  },
});
