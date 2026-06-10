import { describe, expect, test, vi } from "vitest";
import { createServer } from "@/server";

describe("MCP Server", () => {
  test("createServer returns a server instance", () => {
    const server = createServer();
    expect(server).toBeDefined();
  });

  test("server has tool method", () => {
    const server = createServer();
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    expect(typeof server.tool).toBe("function");
  });

  test("server has resource method", () => {
    const server = createServer();
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    expect(typeof server.resource).toBe("function");
  });

  test("server has connect method", () => {
    const server = createServer();
    expect(typeof server.connect).toBe("function");
  });

  test("server has close method", () => {
    const server = createServer();
    expect(typeof server.close).toBe("function");
  });
});

describe("startServer", () => {
  test("creates server, connects transport, and logs startup", async () => {
    // Reset modules first to ensure clean state
    vi.resetModules();

    // Setup mocks BEFORE importing
    const mockConnect = vi.fn().mockResolvedValue(undefined);
    const mockServer = {
      connect: mockConnect,
      tool: vi.fn(),
      resource: vi.fn(),
      prompt: vi.fn(),
    };

    vi.doMock("@modelcontextprotocol/sdk/server/mcp.js", () => ({
      McpServer: vi.fn(function () {
        return mockServer;
      }),
    }));

    const mockTransport = { type: "stdio" };
    vi.doMock("@modelcontextprotocol/sdk/server/stdio.js", () => ({
      StdioServerTransport: vi.fn(function () {
        return mockTransport;
      }),
    }));

    const mockLoggerInfo = vi.fn();
    vi.doMock("@utils", () => ({
      logger: {
        info: mockLoggerInfo,
        debug: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
      },
    }));

    vi.doMock("@tools", () => ({
      registerTools: vi.fn(),
    }));

    vi.doMock("@resources", () => ({
      registerResources: vi.fn(),
    }));

    vi.doMock("@prompts", () => ({
      registerPrompts: vi.fn(),
    }));

    vi.doMock("@config", () => ({
      config: {
        name: "test-mcp",
        version: "0.0.1",
      },
    }));

    // Import fresh module with mocks applied
    const { startServer: freshStartServer } = await import("@/server");

    await freshStartServer();

    expect(mockConnect).toHaveBeenCalledWith(mockTransport);
    expect(mockLoggerInfo).toHaveBeenCalledWith("test-mcp v0.0.1 started");

    // Cleanup
    vi.doUnmock("@modelcontextprotocol/sdk/server/mcp.js");
    vi.doUnmock("@modelcontextprotocol/sdk/server/stdio.js");
    vi.doUnmock("@utils");
    vi.doUnmock("@tools");
    vi.doUnmock("@resources");
    vi.doUnmock("@prompts");
    vi.doUnmock("@config");
    vi.resetModules();
  });
});
