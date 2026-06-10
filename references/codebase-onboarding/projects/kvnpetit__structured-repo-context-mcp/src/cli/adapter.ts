import { defineCommand, type CommandDef } from "citty";
import type { Feature } from "@features/types";
import { zodToCittyArgs } from "@cli/parser";
import { colors } from "@utils";

/**
 * Convert a Feature to a citty CommandDef
 */
export function featureToCittyCommand(feature: Feature): CommandDef {
  return defineCommand({
    meta: {
      name: feature.name,
      description: feature.description,
    },
    args: zodToCittyArgs(feature.schema),
    run({ args }) {
      const result = feature.execute(args);

      const handleResult = (
        res: Awaited<ReturnType<typeof feature.execute>>,
      ): void => {
        if (res.success) {
          const output = res.message ?? JSON.stringify(res.data, null, 2);
          console.log(colors.formatSuccess(output));
        } else {
          console.error(colors.formatError(res.error ?? "Unknown error"));
          process.exit(1);
        }
      };

      if (result instanceof Promise) {
        result.then(handleResult).catch((err: unknown) => {
          const errorMsg = err instanceof Error ? err.message : String(err);
          console.error(colors.formatError(`Unexpected error: ${errorMsg}`));
          process.exit(1);
        });
      } else {
        handleResult(result);
      }
    },
  });
}
