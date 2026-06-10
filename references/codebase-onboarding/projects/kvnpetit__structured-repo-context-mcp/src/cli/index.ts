import { defineCommand, runMain } from "citty";
import { config } from "@config";
import { subCommands } from "@cli/commands";

const main = defineCommand({
  meta: {
    name: config.name,
    version: config.version,
    description: config.description ?? "",
  },
  subCommands,
});

export function runCLI(): void {
  void runMain(main);
}
