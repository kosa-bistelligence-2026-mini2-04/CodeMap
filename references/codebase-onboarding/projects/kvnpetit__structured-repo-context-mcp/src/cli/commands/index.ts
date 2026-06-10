import { features } from "@features";
import { featureToCittyCommand } from "@cli/adapter";
import { serveCommand } from "@cli/commands/serve.command";
import { versionCommand } from "@cli/commands/version.command";

// Feature commands converted from features
const featureCommands = Object.fromEntries(
  features.map((f) => [f.name, featureToCittyCommand(f)]),
);

// All subcommands
export const subCommands = {
  serve: serveCommand,
  version: versionCommand,
  ...featureCommands,
};
