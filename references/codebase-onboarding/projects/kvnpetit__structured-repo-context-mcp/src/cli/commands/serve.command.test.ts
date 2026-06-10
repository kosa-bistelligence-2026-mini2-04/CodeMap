import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { serveCommand } from "@cli/commands/serve.command";
import type { CommandMeta } from "citty";
import { createIndexWatcher } from "@core/embeddings";
import { startServer } from "@/server";
import { logger } from "@utils";

vi.mock("@/server", () => ({
  startServer: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@core/embeddings", () => ({
  createIndexWatcher: vi.fn().mockReturnValue({
    start: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock("@utils", () => ({
  logger: {
    info: vi.fn(),
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

describe("Serve Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Remove signal listeners added by the command
    process.removeAllListeners("SIGINT");
    process.removeAllListeners("SIGTERM");
  });

  test("has correct meta", () => {
    const meta = serveCommand.meta as CommandMeta;

    expect(meta.name).toBe("serve");
    expect(meta.description).toBe("Start the MCP server");
  });

  test("has transport arg with default stdio", () => {
    const args = serveCommand.args as unknown as Record<
      string,
      { default?: string | boolean }
    >;

    expect(args.transport).toBeDefined();
    expect(args.transport?.default).toBe("stdio");
  });

  test("has directory arg with default current directory", () => {
    const args = serveCommand.args as unknown as Record<
      string,
      { default?: string | boolean }
    >;

    expect(args.directory).toBeDefined();
    expect(args.directory?.default).toBe(".");
  });

  test("has watch arg with default true", () => {
    const args = serveCommand.args as unknown as Record<
      string,
      { default?: string | boolean }
    >;

    expect(args.watch).toBeDefined();
    expect(args.watch?.default).toBe(true);
  });

  test("run calls startServer with watch=false", async () => {
    await serveCommand.run?.({
      args: {
        _: [],
        transport: "stdio",
        directory: ".",
        watch: false,
        t: "stdio",
        d: ".",
        w: false,
      },
      rawArgs: [],
      cmd: serveCommand,
    });

    expect(startServer).toHaveBeenCalled();
    expect(createIndexWatcher).not.toHaveBeenCalled();
  });

  test("run creates and starts watcher when watch=true", async () => {
    const mockStart = vi.fn().mockResolvedValue(undefined);
    const mockStop = vi.fn().mockResolvedValue(undefined);
    vi.mocked(createIndexWatcher).mockReturnValue({
      start: mockStart,
      stop: mockStop,
      isRunning: vi.fn().mockReturnValue(true),
    } as unknown as ReturnType<typeof createIndexWatcher>);

    await serveCommand.run?.({
      args: {
        _: [],
        transport: "stdio",
        directory: "/test/dir",
        watch: true,
        t: "stdio",
        d: "/test/dir",
        w: true,
      },
      rawArgs: [],
      cmd: serveCommand,
    });

    expect(createIndexWatcher).toHaveBeenCalledWith({
      directory: "/test/dir",
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
      config: expect.any(Object),
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
      onError: expect.any(Function),
    });
    expect(mockStart).toHaveBeenCalled();
    expect(startServer).toHaveBeenCalled();
  });

  test("logs warning when watcher.start() throws Error", async () => {
    const mockStart = vi
      .fn()
      .mockRejectedValue(new Error("Ollama unavailable"));
    vi.mocked(createIndexWatcher).mockReturnValue({
      start: mockStart,
      stop: vi.fn(),
      isRunning: vi.fn().mockReturnValue(false),
    } as unknown as ReturnType<typeof createIndexWatcher>);

    await serveCommand.run?.({
      args: {
        _: [],
        transport: "stdio",
        directory: ".",
        watch: true,
        t: "stdio",
        d: ".",
        w: true,
      },
      rawArgs: [],
      cmd: serveCommand,
    });

    // eslint-disable-next-line @typescript-eslint/unbound-method
    expect(logger.warn).toHaveBeenCalledWith(
      "Watcher disabled: Ollama unavailable",
    );
    expect(startServer).toHaveBeenCalled();
  });

  test("logs warning when watcher.start() throws non-Error", async () => {
    const mockStart = vi.fn().mockRejectedValue("string error");
    vi.mocked(createIndexWatcher).mockReturnValue({
      start: mockStart,
      stop: vi.fn(),
      isRunning: vi.fn().mockReturnValue(false),
    } as unknown as ReturnType<typeof createIndexWatcher>);

    await serveCommand.run?.({
      args: {
        _: [],
        transport: "stdio",
        directory: ".",
        watch: true,
        t: "stdio",
        d: ".",
        w: true,
      },
      rawArgs: [],
      cmd: serveCommand,
    });

    // eslint-disable-next-line @typescript-eslint/unbound-method
    expect(logger.warn).toHaveBeenCalledWith("Watcher disabled: string error");
    expect(startServer).toHaveBeenCalled();
  });

  test("onError callback logs watcher errors", async () => {
    let capturedOnError: ((error: Error) => void) | undefined;
    vi.mocked(createIndexWatcher).mockImplementation((options) => {
      capturedOnError = options.onError;
      return {
        start: vi.fn().mockResolvedValue(undefined),
        stop: vi.fn(),
        isRunning: vi.fn().mockReturnValue(true),
      } as unknown as ReturnType<typeof createIndexWatcher>;
    });

    await serveCommand.run?.({
      args: {
        _: [],
        transport: "stdio",
        directory: ".",
        watch: true,
        t: "stdio",
        d: ".",
        w: true,
      },
      rawArgs: [],
      cmd: serveCommand,
    });

    // Trigger the onError callback
    expect(capturedOnError).toBeDefined();
    capturedOnError?.(new Error("File read failed"));

    // eslint-disable-next-line @typescript-eslint/unbound-method
    expect(logger.error).toHaveBeenCalledWith(
      "Watcher error: File read failed",
    );
  });

  test("registers SIGINT handler that stops watcher", async () => {
    const mockStop = vi.fn().mockResolvedValue(undefined);
    vi.mocked(createIndexWatcher).mockReturnValue({
      start: vi.fn().mockResolvedValue(undefined),
      stop: mockStop,
      isRunning: vi.fn().mockReturnValue(true),
    } as unknown as ReturnType<typeof createIndexWatcher>);

    const mockExit = vi.spyOn(process, "exit").mockImplementation(() => {
      return undefined as never;
    });

    await serveCommand.run?.({
      args: {
        _: [],
        transport: "stdio",
        directory: ".",
        watch: true,
        t: "stdio",
        d: ".",
        w: true,
      },
      rawArgs: [],
      cmd: serveCommand,
    });

    // Emit SIGINT
    process.emit("SIGINT");

    expect(mockStop).toHaveBeenCalled();
    expect(mockExit).toHaveBeenCalledWith(0);

    mockExit.mockRestore();
  });

  test("registers SIGTERM handler that stops watcher", async () => {
    const mockStop = vi.fn().mockResolvedValue(undefined);
    vi.mocked(createIndexWatcher).mockReturnValue({
      start: vi.fn().mockResolvedValue(undefined),
      stop: mockStop,
      isRunning: vi.fn().mockReturnValue(true),
    } as unknown as ReturnType<typeof createIndexWatcher>);

    const mockExit = vi.spyOn(process, "exit").mockImplementation(() => {
      return undefined as never;
    });

    await serveCommand.run?.({
      args: {
        _: [],
        transport: "stdio",
        directory: ".",
        watch: true,
        t: "stdio",
        d: ".",
        w: true,
      },
      rawArgs: [],
      cmd: serveCommand,
    });

    // Emit SIGTERM
    process.emit("SIGTERM");

    expect(mockStop).toHaveBeenCalled();
    expect(mockExit).toHaveBeenCalledWith(0);

    mockExit.mockRestore();
  });
});
