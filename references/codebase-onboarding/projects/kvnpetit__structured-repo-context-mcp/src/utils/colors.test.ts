import { describe, expect, test } from "vitest";
import { colors } from "@utils/colors";

describe("Colors Utilities", () => {
  test("formatSuccess adds checkmark", () => {
    const result = colors.formatSuccess("Test message");
    expect(result).toContain("Test message");
    expect(result).toContain("✓");
  });

  test("formatError adds cross mark", () => {
    const result = colors.formatError("Error message");
    expect(result).toContain("Error message");
    expect(result).toContain("✗");
  });

  test("formatInfo adds info icon", () => {
    const result = colors.formatInfo("Info message");
    expect(result).toContain("Info message");
    expect(result).toContain("ℹ");
  });

  test("formatWarn adds warning icon", () => {
    const result = colors.formatWarn("Warning message");
    expect(result).toContain("Warning message");
    expect(result).toContain("⚠");
  });

  test("all color functions are defined", () => {
    expect(colors.success).toBeDefined();
    expect(colors.error).toBeDefined();
    expect(colors.warn).toBeDefined();
    expect(colors.info).toBeDefined();
    expect(colors.dim).toBeDefined();
    expect(colors.bold).toBeDefined();
    expect(colors.cyan).toBeDefined();
    expect(colors.magenta).toBeDefined();
  });

  test("composite helpers work", () => {
    expect(colors.successBold("test")).toBeTruthy();
    expect(colors.errorBold("test")).toBeTruthy();
    expect(colors.infoBold("test")).toBeTruthy();
  });

  test("format helpers work", () => {
    expect(colors.formatCommand("cmd")).toBeTruthy();
    expect(colors.formatValue("val")).toBeTruthy();
    expect(colors.formatPath("path")).toBeTruthy();
  });
});
