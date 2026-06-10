import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";
import { createSpinner, withSpinner } from "@utils/spinner";

describe("Spinner Utilities", () => {
  test("createSpinner returns spinner object", () => {
    const spinner = createSpinner("Loading...");

    expect(spinner).toBeDefined();
    expect(typeof spinner.start).toBe("function");
    expect(typeof spinner.stop).toBe("function");
    expect(typeof spinner.succeed).toBe("function");
    expect(typeof spinner.fail).toBe("function");
  });

  test("withSpinner executes function and returns result", async () => {
    const testFn = vi.fn().mockResolvedValue("test result");

    const result = await withSpinner("Processing...", testFn);

    expect(testFn).toHaveBeenCalled();
    expect(result).toBe("test result");
  });

  test("withSpinner handles async functions returning values", async () => {
    const testFn = vi.fn().mockResolvedValue("async result");

    const result = await withSpinner("Processing...", testFn);

    expect(testFn).toHaveBeenCalled();
    expect(result).toBe("async result");
  });

  test("withSpinner with success message", async () => {
    const testFn = vi.fn().mockResolvedValue("done");

    const result = await withSpinner("Processing...", testFn, "Success!");

    expect(result).toBe("done");
  });

  test("withSpinner handles errors", async () => {
    const testFn = vi.fn().mockRejectedValue(new Error("Test error"));

    await expect(withSpinner("Processing...", testFn)).rejects.toThrow(
      "Test error",
    );
  });
});

describe("Spinner with TTY", () => {
  const originalIsTTY = process.stdout.isTTY;

  beforeEach(() => {
    Object.defineProperty(process.stdout, "isTTY", {
      value: true,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(process.stdout, "isTTY", {
      value: originalIsTTY,
      writable: true,
      configurable: true,
    });
  });

  test("withSpinner shows spinner in TTY mode", async () => {
    const testFn = vi.fn().mockResolvedValue("tty result");

    const result = await withSpinner("Loading...", testFn);

    expect(testFn).toHaveBeenCalled();
    expect(result).toBe("tty result");
  });

  test("withSpinner shows spinner with custom success text in TTY", async () => {
    const testFn = vi.fn().mockResolvedValue("done");

    const result = await withSpinner("Working...", testFn, "Completed!");

    expect(result).toBe("done");
  });

  test("withSpinner handles errors in TTY mode", async () => {
    const testFn = vi.fn().mockRejectedValue(new Error("TTY error"));

    await expect(withSpinner("Processing...", testFn)).rejects.toThrow(
      "TTY error",
    );
  });
});
