import { describe, expect, test, vi } from "vitest";
import { versionCommand } from "@cli/commands/version.command";
import type { CommandMeta } from "citty";

describe("Version Command", () => {
  test("has correct meta", () => {
    const meta = versionCommand.meta as CommandMeta;

    expect(meta.name).toBe("version");
    expect(meta.description).toBe("Display version information");
  });

  test("run outputs version", () => {
    const originalLog = console.log;
    console.log = vi.fn();

    versionCommand.run?.(
      {} as Parameters<NonNullable<typeof versionCommand.run>>[0],
    );

    expect(console.log).toHaveBeenCalledWith(
      expect.stringMatching(/^src-mcp v\d+\.\d+\.\d+$/),
    );

    console.log = originalLog;
  });
});
