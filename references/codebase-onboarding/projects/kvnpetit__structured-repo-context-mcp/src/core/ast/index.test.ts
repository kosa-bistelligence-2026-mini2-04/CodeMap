import { afterEach, beforeEach, describe, expect, test } from "vitest";

import {
  extractAST,
  extractText,
  findFirstNode,
  findNodeAtPosition,
  findNodes,
  findNodesByType,
  findNodesByTypes,
  getAncestorTypes,
  getASTStats,
  getLineCount,
  getNodePath,
  serializeAST,
  traverseAST,
} from "@core/ast";
import { getASTRoot, parseCode, resetParser } from "@core/parser";

describe("AST Traversal", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("traverseAST visits all nodes", async () => {
    const code = `const x = 1; const y = 2;`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    const visited: string[] = [];
    traverseAST(root, (node) => {
      visited.push(node.type);
      return undefined;
    });

    expect(visited).toContain("program");
    expect(visited).toContain("lexical_declaration");
    expect(visited.length).toBeGreaterThan(3);
  });

  test("traverseAST can stop early", async () => {
    const code = `const x = 1; const y = 2;`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    const visited: string[] = [];
    traverseAST(root, (node) => {
      visited.push(node.type);
      if (node.type === "lexical_declaration") {
        return false; // Stop
      }
      return true;
    });

    // Should stop after first lexical_declaration
    const lexDecCount = visited.filter(
      (t) => t === "lexical_declaration",
    ).length;
    expect(lexDecCount).toBe(1);
  });

  test("traverseAST provides depth", async () => {
    const code = `function test() { return 1; }`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    let maxDepth = 0;
    traverseAST(root, (_node, depth) => {
      maxDepth = Math.max(maxDepth, depth);
      return undefined;
    });

    expect(maxDepth).toBeGreaterThan(0);
  });
});

describe("AST Finding", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("findNodes finds matching nodes", async () => {
    const code = `const x = 1; let y = 2; const z = 3;`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    const nodes = findNodes(root, (n) => n.type === "lexical_declaration");
    expect(nodes.length).toBe(3);
  });

  test("findNodesByType finds by type", async () => {
    const code = `const x = 1; const y = 2;`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    const nodes = findNodesByType(root, "lexical_declaration");
    expect(nodes.length).toBe(2);
  });

  test("findNodesByTypes finds by multiple types", async () => {
    const code = `const x = 1; function test() {}`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    const nodes = findNodesByTypes(root, [
      "lexical_declaration",
      "function_declaration",
    ]);
    expect(nodes.length).toBe(2);
  });

  test("findFirstNode finds first match", async () => {
    const code = `const x = 1; const y = 2;`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    const node = findFirstNode(root, (n) => n.type === "identifier");
    expect(node).toBeDefined();
    expect(node?.text).toBe("x");
  });

  test("findFirstNode returns undefined if no match", async () => {
    const code = `const x = 1;`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    const node = findFirstNode(root, (n) => n.type === "class_declaration");
    expect(node).toBeUndefined();
  });

  test("findNodeAtPosition finds node at position", async () => {
    const code = `const hello = "world";`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    // Position of "hello" identifier (line 1, column ~6)
    const node = findNodeAtPosition(root, 1, 6);
    expect(node).toBeDefined();
    expect(node?.text).toBe("hello");
  });
});

describe("AST Path", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("getNodePath returns path from root to target", async () => {
    const code = `function test() { const x = 1; }`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    // Find a deep node
    const identifier = findFirstNode(root, (n) => n.text === "x");
    expect(identifier).toBeDefined();

    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion -- validated with expect().toBeDefined()
    const path = getNodePath(root, identifier!);
    expect(path).toBeDefined();
    expect(path?.[0]?.type).toBe("program");
    expect(path?.[path.length - 1]?.text).toBe("x");
  });

  test("getAncestorTypes returns type path", async () => {
    const code = `function test() { const x = 1; }`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    const identifier = findFirstNode(root, (n) => n.text === "x");
    expect(identifier).toBeDefined();

    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion -- validated with expect().toBeDefined()
    const types = getAncestorTypes(root, identifier!);
    expect(types).toContain("program");
    expect(types).toContain("function_declaration");
  });
});

describe("AST Utilities", () => {
  test("extractText extracts text from positions", () => {
    const source = "const hello = 'world';";
    const start = { line: 1, column: 6, offset: 6 };
    const end = { line: 1, column: 11, offset: 11 };

    const text = extractText(source, start, end);
    expect(text).toBe("hello");
  });

  test("getLineCount counts lines", () => {
    expect(getLineCount("line1\nline2\nline3")).toBe(3);
    expect(getLineCount("single")).toBe(1);
    expect(getLineCount("")).toBe(1);
  });
});

describe("AST Extraction", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extractAST with maxDepth limits depth", async () => {
    const code = `function test() { const x = 1; }`;
    const result = await parseCode(code, { language: "javascript" });

    const shallow = extractAST(result.tree.rootNode, { maxDepth: 1 });
    const deep = extractAST(result.tree.rootNode, { maxDepth: 10 });

    // Shallow should not have deeply nested children
    const shallowDepth = getASTStats(shallow).maxDepth;
    const deepDepth = getASTStats(deep).maxDepth;

    expect(shallowDepth).toBeLessThan(deepDepth);
  });

  test("extractAST with includeTypes filters types", async () => {
    const code = `const x = 1; function test() {}`;
    const result = await parseCode(code, { language: "javascript" });

    const filtered = extractAST(result.tree.rootNode, {
      includeTypes: [
        "program",
        "lexical_declaration",
        "variable_declarator",
        "identifier",
        "number",
      ],
    });

    // Should not have function_declaration at top level children
    const hasFunction = filtered.children?.some(
      (c) => c.type === "function_declaration",
    );
    expect(hasFunction).toBeFalsy();
  });

  test("extractAST with excludeTypes removes types", async () => {
    const code = `const x = 1; function test() {}`;
    const result = await parseCode(code, { language: "javascript" });

    const filtered = extractAST(result.tree.rootNode, {
      excludeTypes: ["function_declaration"],
    });

    // Should not have function_declaration
    const hasFunction = filtered.children?.some(
      (c) => c.type === "function_declaration",
    );
    expect(hasFunction).toBeFalsy();
  });
});

describe("AST Serialization", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("serializeAST produces readable output", async () => {
    const code = `const x = 1;`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result, 3);

    const serialized = serializeAST(root);

    expect(serialized).toContain("(program");
    expect(serialized).toContain("lexical_declaration");
  });
});

describe("AST Statistics", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("getASTStats returns accurate stats", async () => {
    const code = `const x = 1; const y = 2;`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    const stats = getASTStats(root);

    expect(stats.totalNodes).toBeGreaterThan(0);
    expect(stats.maxDepth).toBeGreaterThan(0);
    expect(stats.nodeTypes.get("program")).toBe(1);
    expect(stats.nodeTypes.get("lexical_declaration")).toBe(2);
  });
});
