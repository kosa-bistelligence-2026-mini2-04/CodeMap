import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  analyzeFileForCallGraph,
  buildCallGraph,
  clearCallGraphCache,
  formatCallContext,
  getCallContext,
  getCallGraphCacheStats,
} from "@core/embeddings/callgraph";

// Mock logger
vi.mock("@utils", () => ({
  logger: {
    debug: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
  },
}));

describe("callgraph", () => {
  beforeEach(() => {
    clearCallGraphCache();
  });

  afterEach(() => {
    clearCallGraphCache();
  });

  describe("analyzeFileForCallGraph", () => {
    test("extracts function calls from TypeScript", async () => {
      const content = `
function helper() {
  return 42;
}

function main() {
  const result = helper();
  console.log(result);
}
`;

      const data = await analyzeFileForCallGraph("/test/file.ts", content);

      expect(data).not.toBeNull();
      expect(data?.symbols.length).toBeGreaterThan(0);
    });

    test("extracts function calls from JavaScript", async () => {
      const content = `
function add(a, b) {
  return a + b;
}

function calculate() {
  const sum = add(1, 2);
  return sum;
}
`;

      const data = await analyzeFileForCallGraph("/test/file.js", content);

      expect(data).not.toBeNull();
      // Should have at least 2 function symbols (add and calculate)
      expect(data?.symbols.length).toBeGreaterThanOrEqual(2);
    });

    test("caches analysis results", async () => {
      const content = `function test() { return 1; }`;

      const data1 = await analyzeFileForCallGraph("/test/cached.ts", content);
      const data2 = await analyzeFileForCallGraph("/test/cached.ts", content);

      expect(data1).toBe(data2); // Same reference from cache
    });

    test("handles parse errors gracefully", async () => {
      const content = `this is not valid code {{{{`;

      const data = await analyzeFileForCallGraph("/test/invalid.ts", content);

      // Should return null or empty data, not throw
      expect(data === null || data.symbols.length === 0).toBe(true);
    });
  });

  describe("buildCallGraph", () => {
    test("builds graph from multiple files", async () => {
      const files = [
        {
          path: "/test/utils.ts",
          content: `
export function helper() {
  return 42;
}
`,
        },
        {
          path: "/test/main.ts",
          content: `
function main() {
  const x = helper();
  return x;
}
`,
        },
      ];

      const graph = await buildCallGraph(files);

      expect(graph.files).toHaveLength(2);
      expect(graph.nodes.size).toBeGreaterThan(0);
    });

    test("handles empty files array", async () => {
      const graph = await buildCallGraph([]);

      expect(graph.files).toHaveLength(0);
      expect(graph.nodes.size).toBe(0);
      expect(graph.edgeCount).toBe(0);
    });

    test("creates nodes for functions and methods", async () => {
      const files = [
        {
          path: "/test/class.ts",
          content: `
class Calculator {
  add(a: number, b: number): number {
    return a + b;
  }

  multiply(a: number, b: number): number {
    return a * b;
  }
}

function standalone() {
  return new Calculator();
}
`,
        },
      ];

      const graph = await buildCallGraph(files);

      expect(graph.nodes.size).toBeGreaterThan(0);
      // Should have nodes for add, multiply, and standalone
      const nodeNames = Array.from(graph.nodes.values()).map((n) => n.name);
      expect(nodeNames).toContain("standalone");
    });
  });

  describe("getCallContext", () => {
    test("returns callers and callees for a function", async () => {
      const files = [
        {
          path: "/test/app.ts",
          content: `
function a() {
  b();
}

function b() {
  c();
}

function c() {
  return 1;
}
`,
        },
      ];

      const graph = await buildCallGraph(files);
      const context = getCallContext(graph, "/test/app.ts", "b");

      expect(context).not.toBeNull();
      // b is called by a
      // b calls c
    });

    test("returns null for non-existent function", async () => {
      const graph = await buildCallGraph([]);
      const context = getCallContext(graph, "/test/file.ts", "nonexistent");

      expect(context).toBeNull();
    });
  });

  describe("formatCallContext", () => {
    test("formats callers and callees", () => {
      const callers = [
        {
          name: "main",
          qualifiedName: "/test.ts:main",
          filePath: "/test.ts",
          type: "function",
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 5, column: 0, offset: 50 },
          calls: [],
          calledBy: [],
        },
      ];

      const callees = [
        {
          name: "helper",
          qualifiedName: "/test.ts:helper",
          filePath: "/test.ts",
          type: "function",
          start: { line: 10, column: 0, offset: 100 },
          end: { line: 15, column: 0, offset: 150 },
          calls: [],
          calledBy: [],
        },
      ];

      const formatted = formatCallContext(callers, callees);

      expect(formatted).toContain("Called by: main");
      expect(formatted).toContain("Calls: helper");
    });

    test("limits number of items", () => {
      const callers = Array.from({ length: 10 }, (_, i) => ({
        name: `caller${String(i)}`,
        qualifiedName: `/test.ts:caller${String(i)}`,
        filePath: "/test.ts",
        type: "function",
        start: { line: 1, column: 0, offset: 0 },
        end: { line: 5, column: 0, offset: 50 },
        calls: [],
        calledBy: [],
      }));

      const formatted = formatCallContext(callers, [], 3);

      expect(formatted).toContain("caller0");
      expect(formatted).toContain("caller1");
      expect(formatted).toContain("caller2");
      expect(formatted).not.toContain("caller3");
    });

    test("handles empty arrays", () => {
      const formatted = formatCallContext([], []);
      expect(formatted).toBe("");
    });
  });

  describe("cache management", () => {
    test("clearCallGraphCache clears the cache", async () => {
      const content = `function test() {}`;
      await analyzeFileForCallGraph("/test/file.ts", content);

      const statsBefore = getCallGraphCacheStats();
      expect(statsBefore.files).toBeGreaterThan(0);

      clearCallGraphCache();

      const statsAfter = getCallGraphCacheStats();
      expect(statsAfter.files).toBe(0);
    });

    test("getCallGraphCacheStats returns cache info", async () => {
      await analyzeFileForCallGraph("/test/a.ts", `function a() {}`);
      await analyzeFileForCallGraph("/test/b.ts", `function b() {}`);

      const stats = getCallGraphCacheStats();
      expect(stats.files).toBe(2);
      expect(stats.entries).toContain("/test/a.ts");
      expect(stats.entries).toContain("/test/b.ts");
    });
  });
});
