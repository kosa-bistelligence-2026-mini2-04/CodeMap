import { defineCommand } from "citty";
import { config } from "@config";

export const versionCommand = defineCommand({
  meta: {
    name: "version",
    description: "Display version information",
  },
  run() {
    console.log(`${config.name} v${config.version}`);
  },
});
