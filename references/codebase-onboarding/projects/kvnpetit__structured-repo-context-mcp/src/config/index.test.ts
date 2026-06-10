import { describe, expect, test } from "vitest";
import { config, ENV } from "@config";

describe("Config", () => {
  test("config has required fields", () => {
    expect(config.name).toBe("src-mcp");
    expect(config.fullName).toBe("SRC (Structured Repo Context)");
    expect(config.version).toBeDefined();
    expect(config.description).toBeDefined();
  });

  test("config.version is valid semver format", () => {
    expect(config.version).toMatch(/^\d+\.\d+\.\d+$/);
  });
});

describe("ENV", () => {
  test("ENV has required fields", () => {
    expect(typeof ENV.isDev).toBe("boolean");
    expect(typeof ENV.isProd).toBe("boolean");
    expect(typeof ENV.logLevel).toBe("string");
  });

  test("ENV.logLevel defaults to info", () => {
    expect(ENV.logLevel).toBe("info");
  });
});
