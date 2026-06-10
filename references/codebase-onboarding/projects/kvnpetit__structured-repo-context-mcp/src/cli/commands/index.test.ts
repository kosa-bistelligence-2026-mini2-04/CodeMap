import { describe, expect, test } from "vitest";
import { subCommands } from "@cli/commands";

describe("CLI Commands Index", () => {
  test("subCommands contains serve command", () => {
    expect(subCommands.serve).toBeDefined();
  });

  test("subCommands contains version command", () => {
    expect(subCommands.version).toBeDefined();
  });

  test("subCommands contains feature commands", () => {
    // The info feature should be available as a command
    expect(subCommands).toHaveProperty("get_server_info");
  });

  test("all subCommands have meta property", () => {
    for (const [name, command] of Object.entries(subCommands)) {
      expect(command, `Command ${name} should have meta`).toHaveProperty(
        "meta",
      );
    }
  });
});
