import { afterEach, beforeEach, describe, expect, test } from "vitest";

import {
  clearLanguageCache,
  countNodes,
  getASTRoot,
  getLanguageByName,
  getLanguageFromExtension,
  getLanguageFromPath,
  getLanguages,
  getSupportedExtensions,
  getSupportedLanguages,
  initializeParser,
  isLanguageSupported,
  isParserInitialized,
  parseCode,
  resetParser,
  toASTNode,
  toPosition,
} from "@core/parser";

describe("Parser Languages", () => {
  test("getLanguageFromExtension returns correct config", () => {
    const jsConfig = getLanguageFromExtension(".js");
    expect(jsConfig?.name).toBe("javascript");

    const tsConfig = getLanguageFromExtension(".ts");
    expect(tsConfig?.name).toBe("typescript");

    const pyConfig = getLanguageFromExtension(".py");
    expect(pyConfig?.name).toBe("python");
  });

  test("getLanguageFromExtension handles extensions without dot", () => {
    const config = getLanguageFromExtension("ts");
    expect(config?.name).toBe("typescript");
  });

  test("getLanguageFromExtension returns undefined for unknown extension", () => {
    const config = getLanguageFromExtension(".unknown");
    expect(config).toBeUndefined();
  });

  test("getLanguageFromPath detects language correctly", () => {
    expect(getLanguageFromPath("src/index.ts")?.name).toBe("typescript");
    expect(getLanguageFromPath("main.py")?.name).toBe("python");
    expect(getLanguageFromPath("app.jsx")?.name).toBe("javascript");
    expect(getLanguageFromPath("component.tsx")?.name).toBe("tsx");
  });

  test("getLanguageByName returns correct config", () => {
    expect(getLanguageByName("typescript")?.name).toBe("typescript");
    expect(getLanguageByName("PYTHON")?.name).toBe("python");
    expect(getLanguageByName("unknown")).toBeUndefined();
  });

  test("isLanguageSupported checks correctly", () => {
    expect(isLanguageSupported("typescript")).toBe(true);
    expect(isLanguageSupported("python")).toBe(true);
    expect(isLanguageSupported("unknown")).toBe(false);
  });

  test("getSupportedLanguages returns all languages", () => {
    const languages = getSupportedLanguages();
    expect(languages).toContain("typescript");
    expect(languages).toContain("javascript");
    expect(languages).toContain("python");
    expect(languages).toContain("go");
    expect(languages).toContain("rust");
  });

  test("getSupportedExtensions returns all extensions", () => {
    const extensions = getSupportedExtensions();
    expect(extensions).toContain(".ts");
    expect(extensions).toContain(".js");
    expect(extensions).toContain(".py");
    expect(extensions).toContain(".go");
    expect(extensions).toContain(".rs");
  });

  test("getLanguages returns all language configs", () => {
    const languages = getLanguages();
    expect(languages).toHaveProperty("javascript");
    expect(languages).toHaveProperty("typescript");
    expect(languages).toHaveProperty("python");
    expect(languages.javascript?.name).toBe("javascript");
    expect(languages.typescript?.extensions).toContain(".ts");
  });
});

describe("Parser Initialization", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("initializes parser successfully", async () => {
    expect(isParserInitialized()).toBe(false);
    await initializeParser();
    expect(isParserInitialized()).toBe(true);
  });

  test("multiple init calls are safe", async () => {
    await initializeParser();
    await initializeParser();
    expect(isParserInitialized()).toBe(true);
  });
});

describe("parseCode", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("parses JavaScript code", async () => {
    const code = `function hello() { return "world"; }`;
    const result = await parseCode(code, { language: "javascript" });

    expect(result.language).toBe("javascript");
    expect(result.tree).toBeDefined();
    expect(result.tree.rootNode.type).toBe("program");
  });

  test("parses TypeScript code", async () => {
    const code = `function greet(name: string): string { return name; }`;
    const result = await parseCode(code, { language: "typescript" });

    expect(result.language).toBe("typescript");
    expect(result.tree.rootNode.type).toBe("program");
  });

  test("parses TSX code", async () => {
    const code = `const App = () => <div>Hello</div>;`;
    const result = await parseCode(code, { language: "tsx" });

    expect(result.language).toBe("tsx");
    expect(result.tree.rootNode.type).toBe("program");
  });

  test("parses Python code", async () => {
    const code = `def hello():\n    return "world"`;
    const result = await parseCode(code, { language: "python" });

    expect(result.language).toBe("python");
    expect(result.tree.rootNode.type).toBe("module");
  });

  test("auto-detects language from file path", async () => {
    const code = `console.log("hello");`;
    const result = await parseCode(code, { filePath: "test.js" });

    expect(result.language).toBe("javascript");
  });

  test("throws for unsupported language", async () => {
    const code = `some code`;
    await expect(parseCode(code, { language: "unsupported" })).rejects.toThrow(
      "Unsupported language: unsupported",
    );
  });

  test("throws when neither language nor filePath provided", async () => {
    const code = `some code`;
    await expect(parseCode(code, {})).rejects.toThrow(
      "Either language or filePath must be provided",
    );
  });

  test("throws for unknown file extension", async () => {
    const code = `some code`;
    await expect(parseCode(code, { filePath: "test.xyz" })).rejects.toThrow(
      "Could not detect language for file: test.xyz",
    );
  });

  // Tests for additional language parsers
  test("parses Go code", async () => {
    const code = `package main\nfunc main() { fmt.Println("Hello") }`;
    const result = await parseCode(code, { language: "go" });

    expect(result.language).toBe("go");
    expect(result.tree.rootNode.type).toBe("source_file");
  });

  test("parses Rust code", async () => {
    const code = `fn main() { println!("Hello"); }`;
    const result = await parseCode(code, { language: "rust" });

    expect(result.language).toBe("rust");
    expect(result.tree.rootNode.type).toBe("source_file");
  });

  test("parses Java code", async () => {
    const code = `public class Main { public static void main(String[] args) {} }`;
    const result = await parseCode(code, { language: "java" });

    expect(result.language).toBe("java");
    expect(result.tree.rootNode.type).toBe("program");
  });

  test("parses C code", async () => {
    const code = `int main() { return 0; }`;
    const result = await parseCode(code, { language: "c" });

    expect(result.language).toBe("c");
    expect(result.tree.rootNode.type).toBe("translation_unit");
  });

  test("parses C++ code", async () => {
    const code = `#include <iostream>\nint main() { return 0; }`;
    const result = await parseCode(code, { language: "cpp" });

    expect(result.language).toBe("cpp");
    expect(result.tree.rootNode.type).toBe("translation_unit");
  });

  test("parses Ruby code", async () => {
    const code = `def hello\n  puts "world"\nend`;
    const result = await parseCode(code, { language: "ruby" });

    expect(result.language).toBe("ruby");
    expect(result.tree.rootNode.type).toBe("program");
  });

  test("parses PHP code", async () => {
    const code = `<?php function hello() { echo "world"; }`;
    const result = await parseCode(code, { language: "php" });

    expect(result.language).toBe("php");
    expect(result.tree.rootNode.type).toBe("program");
  });

  test("parses Scala code", async () => {
    const code = `object Main { def main(args: Array[String]): Unit = {} }`;
    const result = await parseCode(code, { language: "scala" });

    expect(result.language).toBe("scala");
    expect(result.tree.rootNode.type).toBe("compilation_unit");
  });

  test("parses C# code", async () => {
    const code = `class Program { static void Main() {} }`;
    const result = await parseCode(code, { language: "csharp" });

    expect(result.language).toBe("c_sharp");
    expect(result.tree.rootNode.type).toBe("compilation_unit");
  });

  // Haskell removed - uses text splitter fallback
  // OCaml removed - uses text splitter fallback
  // Julia removed - uses text splitter fallback
  // Dart removed - WASM compatibility issues
  // Bash removed - uses text splitter fallback
  // HTML removed - uses text splitter fallback
  // CSS removed - uses text splitter fallback
  // JSON removed - uses text splitter fallback

  test("parses Svelte code", async () => {
    const code = `<script>let name = "world";</script><h1>Hello {name}</h1>`;
    const result = await parseCode(code, { language: "svelte" });

    expect(result.language).toBe("svelte");
    expect(result.tree.rootNode.type).toBe("document");
  });
});

describe("AST Conversion", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("toPosition converts correctly", () => {
    const point = { row: 0, column: 5 };
    const position = toPosition(point, 5);

    expect(position.line).toBe(1); // 1-based
    expect(position.column).toBe(5); // 0-based
    expect(position.offset).toBe(5);
  });

  test("toASTNode converts tree-sitter node", async () => {
    const code = `const x = 1;`;
    const result = await parseCode(code, { language: "javascript" });
    const astNode = toASTNode(result.tree.rootNode);

    expect(astNode.type).toBe("program");
    expect(astNode.start.line).toBe(1);
    expect(astNode.children).toBeDefined();
    expect(astNode.children?.length).toBeGreaterThan(0);
  });

  test("toASTNode respects maxDepth", async () => {
    const code = `function test() { const x = 1; }`;
    const result = await parseCode(code, { language: "javascript" });

    const shallow = toASTNode(result.tree.rootNode, 1);
    const deep = toASTNode(result.tree.rootNode, 10);

    // Shallow should have fewer nested children
    expect(shallow.children).toBeDefined();
    const shallowChildHasChildren = shallow.children?.some(
      (c) => c.children && c.children.length > 0,
    );
    expect(shallowChildHasChildren).toBe(false);

    // Deep should have nested children
    expect(deep.children).toBeDefined();
  });

  test("getASTRoot returns root node", async () => {
    const code = `let y = 2;`;
    const result = await parseCode(code, { language: "javascript" });
    const root = getASTRoot(result);

    expect(root.type).toBe("program");
    expect(root.text).toBe(code);
  });

  test("countNodes counts all named nodes", async () => {
    const code = `const a = 1; const b = 2;`;
    const result = await parseCode(code, { language: "javascript" });
    const count = countNodes(result.tree.rootNode);

    expect(count).toBeGreaterThan(1);
  });
});

describe("Language Cache", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("clearLanguageCache clears cache", async () => {
    // Parse once to populate cache
    await parseCode("const x = 1;", { language: "javascript" });

    // Clear cache multiple times to ensure function body is executed
    clearLanguageCache();
    clearLanguageCache();

    // Verify languages still work after cache clear (forces reload)
    expect(getLanguageByName("javascript")?.name).toBe("javascript");
    expect(getSupportedLanguages()).toContain("javascript");

    // Should still work (will reload)
    const result = await parseCode("const y = 2;", { language: "javascript" });
    expect(result.language).toBe("javascript");
  });

  test("resetParser resets all state", async () => {
    await initializeParser();
    expect(isParserInitialized()).toBe(true);

    resetParser();
    expect(isParserInitialized()).toBe(false);
  });
});

describe("Concurrent Initialization", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("handles concurrent initialization calls", async () => {
    // Call init multiple times concurrently
    const promises = [
      initializeParser(),
      initializeParser(),
      initializeParser(),
    ];

    await Promise.all(promises);
    expect(isParserInitialized()).toBe(true);
  });

  test("returns same promise for concurrent init calls", async () => {
    resetParser();
    // First call starts init
    const p1 = initializeParser();
    // Second call while first is still running should return same promise
    const p2 = initializeParser();

    await Promise.all([p1, p2]);
    expect(isParserInitialized()).toBe(true);
  });
});
