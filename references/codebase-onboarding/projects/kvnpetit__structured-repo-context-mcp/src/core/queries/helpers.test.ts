import { describe, expect, test } from "vitest";

import type { ASTNode, QueryCapture, QueryMatch } from "@core/ast/types";

import {
  createOffsetTracker,
  deduplicateNodes,
  extractNodes,
  filterCapturesByPrefix,
  findCapture,
  findCaptureByNames,
  findCaptureByPrefix,
  getCaptureKind,
} from "./helpers";

// Helper to create mock captures
function mockCapture(name: string, text: string, offset: number): QueryCapture {
  return {
    name,
    node: {
      type: "identifier",
      text,
      start: { line: 1, column: 0, offset },
      end: { line: 1, column: text.length, offset: offset + text.length },
      isNamed: true,
    },
  };
}

// Helper to create mock matches
function mockMatch(captures: QueryCapture[]): QueryMatch {
  return { pattern: 0, captures };
}

describe("Query Helpers", () => {
  describe("findCapture", () => {
    test("finds capture by exact name", () => {
      const captures = [
        mockCapture("name", "foo", 0),
        mockCapture("definition.function", "bar", 10),
      ];

      const result = findCapture(captures, "name");
      expect(result).toBeDefined();
      expect(result?.name).toBe("name");
      expect(result?.node.text).toBe("foo");
    });

    test("returns undefined when not found", () => {
      const captures = [mockCapture("name", "foo", 0)];
      expect(findCapture(captures, "other")).toBeUndefined();
    });
  });

  describe("findCaptureByNames", () => {
    test("finds first matching capture from list", () => {
      const captures = [
        mockCapture("definition.class", "MyClass", 0),
        mockCapture("name", "MyClass", 10),
      ];

      const result = findCaptureByNames(captures, [
        "definition.function",
        "definition.class",
      ]);
      expect(result?.name).toBe("definition.class");
    });

    test("returns undefined when no names match", () => {
      const captures = [mockCapture("name", "foo", 0)];
      expect(
        findCaptureByNames(captures, [
          "definition.function",
          "definition.class",
        ]),
      ).toBeUndefined();
    });
  });

  describe("findCaptureByPrefix", () => {
    test("finds capture by prefix", () => {
      const captures = [
        mockCapture("name", "foo", 0),
        mockCapture("definition.function", "bar", 10),
      ];

      const result = findCaptureByPrefix(captures, "definition.");
      expect(result?.name).toBe("definition.function");
    });

    test("returns undefined when no prefix matches", () => {
      const captures = [mockCapture("name", "foo", 0)];
      expect(findCaptureByPrefix(captures, "reference.")).toBeUndefined();
    });
  });

  describe("filterCapturesByPrefix", () => {
    test("returns all captures matching prefix", () => {
      const captures = [
        mockCapture("import.source", "foo", 0),
        mockCapture("import.name", "bar", 10),
        mockCapture("other", "baz", 20),
      ];

      const result = filterCapturesByPrefix(captures, "import.");
      expect(result).toHaveLength(2);
      expect(result.map((c) => c.name)).toEqual([
        "import.source",
        "import.name",
      ]);
    });

    test("returns empty array when no matches", () => {
      const captures = [mockCapture("name", "foo", 0)];
      expect(filterCapturesByPrefix(captures, "export.")).toHaveLength(0);
    });
  });

  describe("getCaptureKind", () => {
    test("extracts kind from capture name", () => {
      expect(getCaptureKind("definition.function", "definition.")).toBe(
        "function",
      );
      expect(getCaptureKind("reference.call", "reference.")).toBe("call");
    });

    test("returns original name if prefix not found", () => {
      expect(getCaptureKind("name", "definition.")).toBe("name");
    });
  });

  describe("deduplicateNodes", () => {
    test("removes duplicate nodes based on offset", () => {
      const matches = [
        mockMatch([mockCapture("import.statement", "import A", 0)]),
        mockMatch([mockCapture("import.statement", "import A", 0)]), // duplicate
        mockMatch([mockCapture("import.statement", "import B", 20)]),
      ];

      const result = deduplicateNodes(matches, ["import.statement"]);
      expect(result).toHaveLength(2);
      expect(result[0]?.text).toBe("import A");
      expect(result[1]?.text).toBe("import B");
    });

    test("returns empty array when no matches", () => {
      const matches = [mockMatch([mockCapture("other", "foo", 0)])];
      expect(deduplicateNodes(matches, ["import.statement"])).toHaveLength(0);
    });

    test("skips matches where capture is not found", () => {
      const matches = [
        mockMatch([mockCapture("import.statement", "import A", 0)]),
        mockMatch([mockCapture("unrelated.capture", "ignored", 10)]),
        mockMatch([mockCapture("import.statement", "import B", 20)]),
      ];

      const result = deduplicateNodes(matches, ["import.statement"]);
      expect(result).toHaveLength(2);
    });

    test("returns empty array for empty matches array", () => {
      const result = deduplicateNodes([], ["import.statement"]);
      expect(result).toHaveLength(0);
    });

    test("handles multiple capture names for deduplication", () => {
      const matches = [
        mockMatch([mockCapture("definition.function", "func", 0)]),
        mockMatch([mockCapture("definition.class", "cls", 10)]),
        mockMatch([mockCapture("definition.function", "func", 0)]), // duplicate
      ];

      const result = deduplicateNodes(matches, [
        "definition.function",
        "definition.class",
      ]);
      expect(result).toHaveLength(2);
    });
  });

  describe("extractNodes", () => {
    test("extracts nodes from matches", () => {
      const matches = [
        mockMatch([mockCapture("function.definition", "func1", 0)]),
        mockMatch([mockCapture("function.definition", "func2", 20)]),
      ];

      const result = extractNodes(matches, ["function.definition"]);
      expect(result).toHaveLength(2);
      expect(result[0]?.text).toBe("func1");
      expect(result[1]?.text).toBe("func2");
    });

    test("handles multiple capture names", () => {
      const matches = [
        mockMatch([mockCapture("function.definition", "func1", 0)]),
        mockMatch([mockCapture("method.definition", "method1", 20)]),
      ];

      const result = extractNodes(matches, [
        "function.definition",
        "method.definition",
      ]);
      expect(result).toHaveLength(2);
    });

    test("returns empty array when capture not found in matches", () => {
      const matches = [
        mockMatch([mockCapture("other.capture", "foo", 0)]),
        mockMatch([mockCapture("another.capture", "bar", 10)]),
      ];

      const result = extractNodes(matches, ["nonexistent.capture"]);
      expect(result).toHaveLength(0);
    });

    test("skips matches without matching captures", () => {
      const matches = [
        mockMatch([mockCapture("function.definition", "func1", 0)]),
        mockMatch([mockCapture("other.capture", "ignored", 10)]),
        mockMatch([mockCapture("function.definition", "func2", 20)]),
      ];

      const result = extractNodes(matches, ["function.definition"]);
      expect(result).toHaveLength(2);
      expect(result[0]?.text).toBe("func1");
      expect(result[1]?.text).toBe("func2");
    });

    test("returns empty array for empty matches", () => {
      const result = extractNodes([], ["any.capture"]);
      expect(result).toHaveLength(0);
    });
  });

  describe("createOffsetTracker", () => {
    test("tracks seen nodes by offset", () => {
      const tracker = createOffsetTracker();
      const node1: ASTNode = {
        type: "identifier",
        text: "foo",
        start: { line: 1, column: 0, offset: 0 },
        end: { line: 1, column: 3, offset: 3 },
        isNamed: true,
      };
      const node2: ASTNode = {
        type: "identifier",
        text: "bar",
        start: { line: 1, column: 0, offset: 10 },
        end: { line: 1, column: 3, offset: 13 },
        isNamed: true,
      };

      expect(tracker.has(node1)).toBe(false);
      tracker.add(node1);
      expect(tracker.has(node1)).toBe(true);
      expect(tracker.has(node2)).toBe(false);
    });
  });
});
