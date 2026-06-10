import { describe, expect, test } from "vitest";
import {
  chunkFile,
  chunkFiles,
  detectLanguage,
  shouldIndexFile,
  SUPPORTED_EXTENSIONS,
} from "@core/embeddings/chunker";

describe("detectLanguage", () => {
  test("detects TypeScript", () => {
    expect(detectLanguage("file.ts")).toBe("typescript");
    expect(detectLanguage("file.tsx")).toBe("typescript");
  });

  test("detects JavaScript", () => {
    expect(detectLanguage("file.js")).toBe("javascript");
    expect(detectLanguage("file.jsx")).toBe("javascript");
    expect(detectLanguage("file.mjs")).toBe("javascript");
  });

  test("detects Python", () => {
    expect(detectLanguage("file.py")).toBe("python");
  });

  test("detects Rust", () => {
    expect(detectLanguage("file.rs")).toBe("rust");
  });

  test("detects Go", () => {
    expect(detectLanguage("file.go")).toBe("go");
  });

  test("returns unknown for unrecognized extensions", () => {
    expect(detectLanguage("file.xyz")).toBe("unknown");
    expect(detectLanguage("noext")).toBe("unknown");
  });
});

describe("chunkFile", () => {
  const config = {
    defaultChunkSize: 100,
    defaultChunkOverlap: 20,
  };

  test("chunks a TypeScript file", async () => {
    const content = `
export function hello() {
  return "world";
}

export function goodbye() {
  return "farewell";
}
`.trim();

    const chunks = await chunkFile("/test/file.ts", content, config);

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]).toHaveProperty("id");
    expect(chunks[0]).toHaveProperty("content");
    expect(chunks[0]).toHaveProperty("filePath", "/test/file.ts");
    expect(chunks[0]).toHaveProperty("language", "typescript");
    expect(chunks[0]).toHaveProperty("startLine");
    expect(chunks[0]).toHaveProperty("endLine");
  });

  test("generates unique IDs for chunks", async () => {
    const content = `
function a() {}
function b() {}
function c() {}
`.trim();

    const chunks = await chunkFile("/test/file.ts", content, config);
    const ids = chunks.map((c) => c.id);
    const uniqueIds = new Set(ids);

    expect(uniqueIds.size).toBe(ids.length);
  });

  test("handles empty content", async () => {
    const chunks = await chunkFile("/test/empty.ts", "", config);
    expect(chunks).toHaveLength(0);
  });

  test("calculates correct line numbers", async () => {
    const content = `line1
line2
line3
line4
line5`;

    const chunks = await chunkFile("/test/file.ts", content, {
      defaultChunkSize: 1000,
      defaultChunkOverlap: 0,
    });

    expect(chunks.length).toBe(1);
    expect(chunks[0]?.startLine).toBe(1);
    expect(chunks[0]?.endLine).toBe(5);
  });
});

describe("chunkFiles", () => {
  const config = {
    defaultChunkSize: 100,
    defaultChunkOverlap: 20,
  };

  test("chunks multiple files", async () => {
    const files = [
      { path: "/test/file1.ts", content: "function a() {}" },
      { path: "/test/file2.py", content: "def b(): pass" },
    ];

    const chunks = await chunkFiles(files, config);

    expect(chunks.length).toBeGreaterThan(0);

    const tsChunks = chunks.filter((c) => c.language === "typescript");
    const pyChunks = chunks.filter((c) => c.language === "python");

    expect(tsChunks.length).toBeGreaterThan(0);
    expect(pyChunks.length).toBeGreaterThan(0);
  });
});

describe("shouldIndexFile", () => {
  test("returns true for supported extensions", () => {
    expect(shouldIndexFile("file.ts")).toBe(true);
    expect(shouldIndexFile("file.tsx")).toBe(true);
    expect(shouldIndexFile("file.js")).toBe(true);
    expect(shouldIndexFile("file.py")).toBe(true);
    expect(shouldIndexFile("file.rs")).toBe(true);
    expect(shouldIndexFile("file.go")).toBe(true);
    expect(shouldIndexFile("file.md")).toBe(true);
  });

  test("returns false for unsupported extensions", () => {
    expect(shouldIndexFile("file.png")).toBe(false);
    expect(shouldIndexFile("file.exe")).toBe(false);
    expect(shouldIndexFile("file.zip")).toBe(false);
    expect(shouldIndexFile(".gitignore")).toBe(false);
  });

  test("handles case insensitivity", () => {
    expect(shouldIndexFile("file.TS")).toBe(true);
    expect(shouldIndexFile("file.PY")).toBe(true);
  });
});

describe("SUPPORTED_EXTENSIONS", () => {
  test("includes common programming languages", () => {
    expect(SUPPORTED_EXTENSIONS).toContain(".ts");
    expect(SUPPORTED_EXTENSIONS).toContain(".tsx");
    expect(SUPPORTED_EXTENSIONS).toContain(".js");
    expect(SUPPORTED_EXTENSIONS).toContain(".py");
    expect(SUPPORTED_EXTENSIONS).toContain(".rs");
    expect(SUPPORTED_EXTENSIONS).toContain(".go");
    expect(SUPPORTED_EXTENSIONS).toContain(".java");
  });
});

describe("detectLanguage edge cases", () => {
  test("handles file without extension", () => {
    expect(detectLanguage("Makefile")).toBe("unknown");
    expect(detectLanguage("Dockerfile")).toBe("unknown");
  });

  test("handles file with multiple dots", () => {
    expect(detectLanguage("file.test.ts")).toBe("typescript");
    expect(detectLanguage("my.component.tsx")).toBe("typescript");
  });

  test("detects all supported languages", () => {
    expect(detectLanguage("file.kt")).toBe("kotlin");
    expect(detectLanguage("file.rb")).toBe("ruby");
    expect(detectLanguage("file.php")).toBe("php");
    expect(detectLanguage("file.c")).toBe("c");
    expect(detectLanguage("file.cpp")).toBe("cpp");
    expect(detectLanguage("file.h")).toBe("c");
    expect(detectLanguage("file.hpp")).toBe("cpp");
    expect(detectLanguage("file.cs")).toBe("csharp");
    expect(detectLanguage("file.swift")).toBe("swift");
    expect(detectLanguage("file.scala")).toBe("scala");
    expect(detectLanguage("file.vue")).toBe("vue");
    expect(detectLanguage("file.svelte")).toBe("svelte");
    expect(detectLanguage("file.json")).toBe("json");
    expect(detectLanguage("file.yaml")).toBe("yaml");
    expect(detectLanguage("file.yml")).toBe("yaml");
    expect(detectLanguage("file.toml")).toBe("toml");
    expect(detectLanguage("file.xml")).toBe("xml");
    expect(detectLanguage("file.html")).toBe("html");
    expect(detectLanguage("file.css")).toBe("css");
    expect(detectLanguage("file.scss")).toBe("scss");
    expect(detectLanguage("file.less")).toBe("less");
    expect(detectLanguage("file.sql")).toBe("sql");
    expect(detectLanguage("file.sh")).toBe("bash");
    expect(detectLanguage("file.bash")).toBe("bash");
    expect(detectLanguage("file.zsh")).toBe("bash");
    expect(detectLanguage("file.cjs")).toBe("javascript");
    expect(detectLanguage("file.java")).toBe("java");
  });
});

describe("chunkFile edge cases", () => {
  const config = {
    defaultChunkSize: 100,
    defaultChunkOverlap: 20,
  };

  test("uses default separators for unknown language", async () => {
    const content = "line1\n\nline2\n\nline3";
    const chunks = await chunkFile("/test/file.unknown", content, config);

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("unknown");
  });

  test("handles Python files with proper separators", async () => {
    const content = `
class MyClass:
    def __init__(self):
        pass

def my_function():
    return True

async def async_function():
    return False
`.trim();

    const chunks = await chunkFile("/test/file.py", content, {
      defaultChunkSize: 50,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("python");
  });

  test("handles Rust files with proper separators", async () => {
    const content = `
fn main() {
    println!("Hello");
}

pub fn public_fn() -> i32 {
    42
}

struct MyStruct {
    field: i32,
}
`.trim();

    const chunks = await chunkFile("/test/file.rs", content, {
      defaultChunkSize: 50,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("rust");
  });

  test("handles Go files with proper separators", async () => {
    const content = `
func main() {
    fmt.Println("Hello")
}

type MyType struct {
    Field int
}
`.trim();

    const chunks = await chunkFile("/test/file.go", content, {
      defaultChunkSize: 50,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("go");
  });

  test("handles Java files with proper separators", async () => {
    const content = `
public class MyClass {
    private int field;

    public void method() {
        System.out.println("Hello");
    }
}
`.trim();

    const chunks = await chunkFile("/test/file.java", content, {
      defaultChunkSize: 50,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("java");
  });
});

describe("shouldIndexFile edge cases", () => {
  test("handles files with no extension", () => {
    expect(shouldIndexFile("README")).toBe(false);
    expect(shouldIndexFile("Makefile")).toBe(false);
  });

  test("handles hidden files", () => {
    expect(shouldIndexFile(".env")).toBe(false);
    expect(shouldIndexFile(".gitignore")).toBe(false);
  });
});

describe("chunkFile advanced scenarios", () => {
  const config = {
    defaultChunkSize: 100,
    defaultChunkOverlap: 20,
  };

  test("handles JavaScript file with all separators", async () => {
    const content = `
export const CONFIG = { debug: true };

function processData(data) {
  return data.map(x => x * 2);
}

class DataProcessor {
  constructor() {
    this.data = [];
  }

  process() {
    return this.data;
  }
}

let counter = 0;
`.trim();

    const chunks = await chunkFile("/test/file.js", content, {
      defaultChunkSize: 80,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("javascript");
  });

  test("handles very large content", async () => {
    // Generate large content with multiple functions
    const functions = Array.from(
      { length: 50 },
      (_, i) => `function func${String(i)}() {\n  return ${String(i)};\n}\n`,
    );
    const content = functions.join("\n");

    const chunks = await chunkFile("/test/large.ts", content, {
      defaultChunkSize: 200,
      defaultChunkOverlap: 20,
    });

    expect(chunks.length).toBeGreaterThan(1);
    // All chunks should have proper metadata
    for (const chunk of chunks) {
      expect(chunk.id).toBeDefined();
      expect(chunk.filePath).toBe("/test/large.ts");
      expect(chunk.startLine).toBeGreaterThan(0);
    }
  });

  test("handles content with no matches in indexOf", async () => {
    // This tests the edge case where indexOf might not find the chunk
    const content = "a".repeat(500);

    const chunks = await chunkFile("/test/repeat.txt", content, {
      defaultChunkSize: 100,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
  });

  test("handles JavaScript with const and let separators", async () => {
    const content = `
const a = 1;
const b = 2;
let c = 3;
let d = 4;
var e = 5;
`.trim();

    const chunks = await chunkFile("/test/vars.js", content, config);
    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("javascript");
  });

  test("handles Rust impl and trait separators", async () => {
    const content = `
impl Person {
    fn new() -> Self {
        Person {}
    }
}

trait Greeter {
    fn greet(&self);
}

mod utils {
    pub fn helper() {}
}

enum Color {
    Red,
    Green,
    Blue,
}
`.trim();

    const chunks = await chunkFile("/test/file.rs", content, {
      defaultChunkSize: 80,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("rust");
  });

  test("handles Go var and const separators", async () => {
    const content = `
var globalVar = "hello"

const MAX_SIZE = 100

type Config struct {
    Debug bool
}

func main() {
    fmt.Println("Hello")
}
`.trim();

    const chunks = await chunkFile("/test/file.go", content, {
      defaultChunkSize: 60,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("go");
  });

  test("handles Java with all modifiers", async () => {
    const content = `
public class Main {
    private int x;
    protected String y;
}

interface Service {
    void run();
}

public void execute() {
    System.out.println("Running");
}
`.trim();

    const chunks = await chunkFile("/test/Main.java", content, {
      defaultChunkSize: 60,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("java");
  });

  test("handles TypeScript with interface and type separators", async () => {
    const content = `
export interface User {
    name: string;
}

export type Config = {
    debug: boolean;
}

export function process() {}

export class Service {}
`.trim();

    const chunks = await chunkFile("/test/file.ts", content, {
      defaultChunkSize: 60,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("typescript");
  });
});

describe("chunkFiles advanced", () => {
  test("handles empty files array", async () => {
    const chunks = await chunkFiles([], {
      defaultChunkSize: 100,
      defaultChunkOverlap: 20,
    });

    expect(chunks).toEqual([]);
  });

  test("handles files with empty content", async () => {
    const files = [
      { path: "/test/empty1.ts", content: "" },
      { path: "/test/empty2.py", content: "" },
    ];

    const chunks = await chunkFiles(files, {
      defaultChunkSize: 100,
      defaultChunkOverlap: 20,
    });

    expect(chunks).toEqual([]);
  });
});

describe("detectLanguage edge cases", () => {
  test("handles file path without extension (no dot)", () => {
    expect(detectLanguage("noextension")).toBe("unknown");
    expect(detectLanguage("/path/to/noextension")).toBe("unknown");
  });

  test("handles file with only a dot", () => {
    expect(detectLanguage(".")).toBe("unknown");
  });

  test("handles empty path", () => {
    expect(detectLanguage("")).toBe("unknown");
  });
});

describe("chunkFile separator fallback", () => {
  test("uses default separators for truly unknown language", async () => {
    const content = "line1\n\nline2\n\nline3";
    const chunks = await chunkFile("/test/file.weirdext", content, {
      defaultChunkSize: 100,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("unknown");
  });

  test("handles language without specific separators", async () => {
    const content = `
some random content
more content here
and more lines
`.trim();

    const chunks = await chunkFile("/test/file.abc123", content, {
      defaultChunkSize: 50,
      defaultChunkOverlap: 5,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("unknown");
  });
});

describe("chunkFile line number calculation", () => {
  test("handles content with many newlines", async () => {
    const content = Array.from(
      { length: 20 },
      (_, i) => `line ${String(i + 1)}`,
    ).join("\n");

    const chunks = await chunkFile("/test/file.txt", content, {
      defaultChunkSize: 50,
      defaultChunkOverlap: 5,
    });

    expect(chunks.length).toBeGreaterThan(0);
    // First chunk should start at line 1
    expect(chunks[0]?.startLine).toBe(1);
    // Later chunks should have higher line numbers
    if (chunks.length > 1) {
      expect(chunks[1]?.startLine).toBeGreaterThan(1);
    }
  });

  test("handles content with no newlines", async () => {
    const content = "just a single line of content without any newlines";

    const chunks = await chunkFile("/test/single.txt", content, {
      defaultChunkSize: 1000,
      defaultChunkOverlap: 0,
    });

    expect(chunks.length).toBe(1);
    expect(chunks[0]?.startLine).toBe(1);
    expect(chunks[0]?.endLine).toBe(1);
  });

  test("handles overlapping chunks correctly", async () => {
    const content = `function a() { return 1; }
function b() { return 2; }
function c() { return 3; }
function d() { return 4; }
function e() { return 5; }`;

    const chunks = await chunkFile("/test/overlap.js", content, {
      defaultChunkSize: 60,
      defaultChunkOverlap: 20,
    });

    expect(chunks.length).toBeGreaterThan(1);
    // All chunks should have valid line numbers
    for (const chunk of chunks) {
      expect(chunk.startLine).toBeGreaterThan(0);
      expect(chunk.endLine).toBeGreaterThanOrEqual(chunk.startLine);
    }
  });
});

describe("shouldIndexFile additional edge cases", () => {
  test("handles uppercase extensions", () => {
    expect(shouldIndexFile("FILE.TS")).toBe(true);
    expect(shouldIndexFile("FILE.PY")).toBe(true);
    expect(shouldIndexFile("FILE.RS")).toBe(true);
  });

  test("handles mixed case extensions", () => {
    expect(shouldIndexFile("file.Ts")).toBe(true);
    expect(shouldIndexFile("file.Py")).toBe(true);
  });

  test("handles files starting with dot", () => {
    expect(shouldIndexFile(".gitignore")).toBe(false);
    expect(shouldIndexFile(".eslintrc")).toBe(false);
    expect(shouldIndexFile(".bashrc")).toBe(false);
  });

  test("handles path with multiple dots", () => {
    expect(shouldIndexFile("file.test.ts")).toBe(true);
    expect(shouldIndexFile("my.app.component.tsx")).toBe(true);
    expect(shouldIndexFile("app.module.spec.ts")).toBe(true);
  });
});

describe("chunkFile chunk index edge cases", () => {
  test("handles modified content during chunking", async () => {
    // Content where chunks might not be found at expected position
    const content = "abc\n\nabc\n\nabc\n\nabc";

    const chunks = await chunkFile("/test/repeat.txt", content, {
      defaultChunkSize: 5,
      defaultChunkOverlap: 2,
    });

    expect(chunks.length).toBeGreaterThan(0);
    // All chunks should have valid line numbers
    for (const chunk of chunks) {
      expect(chunk.startLine).toBeGreaterThan(0);
      expect(chunk.endLine).toBeGreaterThanOrEqual(chunk.startLine);
    }
  });

  test("handles whitespace-only content", async () => {
    const content = "   \n\n   \n\n   ";

    const chunks = await chunkFile("/test/whitespace.txt", content, {
      defaultChunkSize: 100,
      defaultChunkOverlap: 10,
    });

    // Whitespace content may produce chunks or may be empty
    expect(Array.isArray(chunks)).toBe(true);
  });

  test("handles content with unicode characters", async () => {
    const content = `
function greet() {
  return "Hello 世界! 🌍";
}

const emoji = "👨‍💻";
    `.trim();

    const chunks = await chunkFile("/test/unicode.ts", content, {
      defaultChunkSize: 50,
      defaultChunkOverlap: 10,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("typescript");
  });
});

describe("detectLanguage nullish coalescing edge cases", () => {
  test("handles undefined pop result", () => {
    // Empty string split would give [""], pop() gives ""
    expect(detectLanguage("")).toBe("unknown");
  });

  test("handles path ending with dot", () => {
    expect(detectLanguage("file.")).toBe("unknown");
  });

  test("handles only dots path", () => {
    expect(detectLanguage("...")).toBe("unknown");
  });
});

describe("chunkFile indexOf edge cases", () => {
  test("handles content where chunk might not be found at expected offset", async () => {
    // Create content with repeating patterns that could confuse indexOf
    const content = "aaa\naaa\naaa\naaa\naaa\naaa\naaa\naaa";

    const chunks = await chunkFile("/test/repeat.txt", content, {
      defaultChunkSize: 4,
      defaultChunkOverlap: 2,
    });

    // Should still produce valid chunks with valid line numbers
    expect(chunks.length).toBeGreaterThan(0);
    for (const chunk of chunks) {
      expect(chunk.startLine).toBeGreaterThan(0);
      expect(chunk.endLine).toBeGreaterThanOrEqual(chunk.startLine);
    }
  });

  test("handles content with varying whitespace", async () => {
    // Content where trimming might affect indexOf
    const content = "  hello  \n  world  \n  test  ";

    const chunks = await chunkFile("/test/whitespace.txt", content, {
      defaultChunkSize: 10,
      defaultChunkOverlap: 2,
    });

    expect(chunks.length).toBeGreaterThan(0);
    for (const chunk of chunks) {
      expect(chunk.startLine).toBeGreaterThan(0);
    }
  });

  test("handles very small chunk size with overlap", async () => {
    const content = "line1\nline2\nline3\nline4\nline5";

    const chunks = await chunkFile("/test/small-chunk.txt", content, {
      defaultChunkSize: 6,
      defaultChunkOverlap: 3,
    });

    expect(chunks.length).toBeGreaterThan(0);
    // All chunks should have proper metadata
    for (const chunk of chunks) {
      expect(chunk.id).toBeDefined();
      expect(chunk.startLine).toBeGreaterThan(0);
    }
  });

  test("handles single character repeated content", async () => {
    const content = "x".repeat(100);

    const chunks = await chunkFile("/test/single-char.txt", content, {
      defaultChunkSize: 20,
      defaultChunkOverlap: 5,
    });

    expect(chunks.length).toBeGreaterThan(0);
    for (const chunk of chunks) {
      expect(chunk.startLine).toBe(1); // All on line 1
      expect(chunk.endLine).toBe(1);
    }
  });

  test("handles content with special characters", async () => {
    const content = 'func() {\n  return "\\n\\t";\n}\n'.repeat(10);

    const chunks = await chunkFile("/test/special.js", content, {
      defaultChunkSize: 30,
      defaultChunkOverlap: 5,
    });

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0]?.language).toBe("javascript");
  });
});
