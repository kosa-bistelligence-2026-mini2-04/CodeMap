import { describe, expect, test } from "vitest";
import { logger, colors, createSpinner, withSpinner } from "@utils/index";

describe("Utils Index", () => {
  test("exports logger", () => {
    expect(logger).toBeDefined();
    expect(typeof logger.info).toBe("function");
    expect(typeof logger.error).toBe("function");
  });

  test("exports colors", () => {
    expect(colors).toBeDefined();
    expect(typeof colors.formatSuccess).toBe("function");
    expect(typeof colors.formatError).toBe("function");
  });

  test("exports createSpinner", () => {
    expect(createSpinner).toBeDefined();
    expect(typeof createSpinner).toBe("function");
  });

  test("exports withSpinner", () => {
    expect(withSpinner).toBeDefined();
    expect(typeof withSpinner).toBe("function");
  });
});
