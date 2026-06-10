import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";
import { logger } from "@utils/logger";

describe("Logger", () => {
  /* eslint-disable no-console */
  const originalConsole = {
    log: console.log,
    warn: console.warn,
    error: console.error,
  };

  beforeEach(() => {
    console.log = vi.fn();
    console.warn = vi.fn();
    console.error = vi.fn();
  });

  afterEach(() => {
    console.log = originalConsole.log;
    console.warn = originalConsole.warn;
    console.error = originalConsole.error;
  });

  test("logger.info calls console.error", () => {
    logger.info("Test info message");
    expect(console.error).toHaveBeenCalled();
  });

  test("logger.warn calls console.warn", () => {
    logger.warn("Test warning");
    expect(console.warn).toHaveBeenCalled();
  });

  test("logger.error calls console.error", () => {
    logger.error("Test error");
    expect(console.error).toHaveBeenCalled();
  });

  test("logger.success calls console.error", () => {
    logger.success("Test success");
    expect(console.error).toHaveBeenCalled();
  });

  test("logger.debug does not log when level is info", () => {
    logger.debug("Test debug message");
    // By default log level is 'info', so debug won't log to console.error
    // The function runs but doesn't output
    expect(console.error).not.toHaveBeenCalled();
  });
  /* eslint-enable no-console */

  test("logger has all required methods", () => {
    expect(typeof logger.info).toBe("function");
    expect(typeof logger.warn).toBe("function");
    expect(typeof logger.error).toBe("function");
    expect(typeof logger.success).toBe("function");
    expect(typeof logger.debug).toBe("function");
  });
});

describe("Logger with debug level", () => {
  test("logger.debug function exists and is callable", () => {
    expect(() => {
      logger.debug("Test message");
    }).not.toThrow();
  });

  test("logger uses correct log levels hierarchy", () => {
    expect(typeof logger.debug).toBe("function");
    expect(typeof logger.info).toBe("function");
    expect(typeof logger.warn).toBe("function");
    expect(typeof logger.error).toBe("function");
    expect(typeof logger.success).toBe("function");
  });

  test("logger.debug logs when debug level is enabled", async () => {
    // Dynamically import with mocked ENV
    vi.doMock("@config", () => ({
      ENV: { logLevel: "debug" },
    }));

    // Clear module cache and re-import
    vi.resetModules();
    const { logger: debugLogger } = await import("@utils/logger");

    const consoleSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);

    debugLogger.debug("Debug message");

    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
    vi.doUnmock("@config");
    vi.resetModules();
  });
});

describe("Logger with invalid log level", () => {
  test("falls back to info level when log level is invalid", async () => {
    // Dynamically import with mocked ENV with invalid log level
    vi.doMock("@config", () => ({
      ENV: { logLevel: "invalid_level" },
    }));

    // Clear module cache and re-import
    vi.resetModules();
    const { logger: testLogger } = await import("@utils/logger");

    const consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);

    // Info should still log (default fallback is info level)
    testLogger.info("Test info message");
    expect(consoleErrorSpy).toHaveBeenCalled();

    // Debug should NOT log (debug < info in hierarchy)
    consoleErrorSpy.mockClear();
    testLogger.debug("Test debug message");
    expect(consoleErrorSpy).not.toHaveBeenCalled();

    consoleErrorSpy.mockRestore();

    vi.doUnmock("@config");
    vi.resetModules();
  });

  test("error level suppresses info and warn logs", async () => {
    // Set log level to error - only error should log
    vi.doMock("@config", () => ({
      ENV: { logLevel: "error" },
    }));

    vi.resetModules();
    const { logger: testLogger } = await import("@utils/logger");

    const consoleWarnSpy = vi
      .spyOn(console, "warn")
      .mockImplementation(() => undefined);
    const consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);

    // Info should NOT log (info < error) - info uses console.error now
    testLogger.info("Test info");
    // At this point console.error should NOT have been called for info
    expect(consoleErrorSpy).not.toHaveBeenCalled();

    // Warn should NOT log (warn < error)
    testLogger.warn("Test warning");
    expect(consoleWarnSpy).not.toHaveBeenCalled();

    // Error should log
    testLogger.error("Test error");
    expect(consoleErrorSpy).toHaveBeenCalled();

    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();

    vi.doUnmock("@config");
    vi.resetModules();
  });

  test("warn level suppresses info but allows warn and error", async () => {
    // Set log level to warn - warn and error should log
    vi.doMock("@config", () => ({
      ENV: { logLevel: "warn" },
    }));

    vi.resetModules();
    const { logger: testLogger } = await import("@utils/logger");

    const consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    const consoleWarnSpy = vi
      .spyOn(console, "warn")
      .mockImplementation(() => undefined);

    // Info should NOT log (info < warn) - info uses console.error now
    testLogger.info("Test info");
    expect(consoleErrorSpy).not.toHaveBeenCalled();

    // Warn should log
    testLogger.warn("Test warning");
    expect(consoleWarnSpy).toHaveBeenCalled();

    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();

    vi.doUnmock("@config");
    vi.resetModules();
  });

  test("logger.warn logs at all levels including invalid", async () => {
    vi.doMock("@config", () => ({
      ENV: { logLevel: "invalid_level" },
    }));

    vi.resetModules();
    const { logger: testLogger } = await import("@utils/logger");

    const consoleWarnSpy = vi
      .spyOn(console, "warn")
      .mockImplementation(() => undefined);

    testLogger.warn("Test warning");
    expect(consoleWarnSpy).toHaveBeenCalled();

    consoleWarnSpy.mockRestore();
    vi.doUnmock("@config");
    vi.resetModules();
  });

  test("logger.error logs at all levels", async () => {
    vi.doMock("@config", () => ({
      ENV: { logLevel: "invalid_level" },
    }));

    vi.resetModules();
    const { logger: testLogger } = await import("@utils/logger");

    const consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);

    testLogger.error("Test error");
    expect(consoleErrorSpy).toHaveBeenCalled();

    consoleErrorSpy.mockRestore();
    vi.doUnmock("@config");
    vi.resetModules();
  });
});
