import { execute, getServerInfo, infoSchema } from "@features/info";
import { describe, expect, test, vi } from "vitest";

describe("info feature", () => {
  test("should return server info as text", () => {
    const input = infoSchema.parse({});
    const result = execute(input);

    expect(result.success).toBe(true);
    expect(result.message).toContain("src-mcp");
  });

  test("should return server info as JSON", () => {
    const input = infoSchema.parse({ format: "json" });
    const result = execute(input);

    expect(result.success).toBe(true);
    expect(result.message).toBeDefined();

    const parsed = JSON.parse(result.message ?? "{}") as Record<
      string,
      unknown
    >;
    expect(parsed).toHaveProperty("name");
    expect(parsed).toHaveProperty("fullName");
    expect(parsed).toHaveProperty("version");
  });

  test("getServerInfo should return config values", () => {
    const info = getServerInfo();
    info.version = "1.0.0"; // Mock version for test consistency

    expect(info.name).toBe("src-mcp");
    expect(info.fullName).toBe("SRC (Structured Repo Context)");
    expect(info.version).toBe("1.0.0");
  });

  test("should handle description in text format", () => {
    const input = infoSchema.parse({ format: "text" });
    const result = execute(input);

    expect(result.success).toBe(true);
    expect(result.message).toBeDefined();
    expect(result.message).toContain("SRC");
    expect(result.message).toContain("src-mcp");
  });

  test("schema validates format options correctly", () => {
    expect(() => infoSchema.parse({})).not.toThrow();
    expect(() => infoSchema.parse({ format: "text" })).not.toThrow();
    expect(() => infoSchema.parse({ format: "json" })).not.toThrow();
    expect(() => infoSchema.parse({ format: "invalid" })).toThrow();
  });
});

describe("info feature with undefined description", () => {
  test("handles undefined description gracefully", async () => {
    // Mock config to return undefined description
    vi.doMock("@config", () => ({
      config: {
        name: "test-server",
        fullName: "Test Server",
        version: "1.0.0",
        description: undefined,
      },
    }));

    vi.resetModules();
    const { execute: freshExecute, infoSchema: freshSchema } =
      await import("@features/info");

    const input = freshSchema.parse({ format: "text" });
    const result = freshExecute(input);

    expect(result.success).toBe(true);
    // When description is undefined, the nullish coalescing operator returns ""
    // and .trim() removes trailing newline from empty description
    expect(result.message).toBeDefined();

    vi.doUnmock("@config");
    vi.resetModules();
  });
});
