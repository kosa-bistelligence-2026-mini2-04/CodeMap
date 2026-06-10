import { afterEach, beforeEach, describe, expect, test } from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import {
  readPathAliases,
  readPathAliasesCached,
  clearPathAliasCache,
} from "./tsconfig";

describe("readPathAliases", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "tsconfig-test-"));
    clearPathAliasCache();
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
    clearPathAliasCache();
  });

  test("returns empty object when no tsconfig.json exists", () => {
    const result = readPathAliases(tempDir);
    expect(result).toEqual({});
  });

  test("parses simple path aliases", () => {
    const tsconfig = {
      compilerOptions: {
        baseUrl: ".",
        paths: {
          "@core": ["src/core"],
          "@utils": ["src/utils"],
        },
      },
    };

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    const result = readPathAliases(tempDir);

    expect(result["@core"]).toBe("src/core");
    expect(result["@utils"]).toBe("src/utils");
  });

  test("parses wildcard path aliases", () => {
    const tsconfig = {
      compilerOptions: {
        baseUrl: ".",
        paths: {
          "@core/*": ["src/core/*"],
          "@utils/*": ["src/utils/*"],
        },
      },
    };

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    const result = readPathAliases(tempDir);

    expect(result["@core/"]).toBe("src/core/");
    expect(result["@utils/"]).toBe("src/utils/");
  });

  test("parses mixed exact and wildcard aliases", () => {
    const tsconfig = {
      compilerOptions: {
        baseUrl: ".",
        paths: {
          "@config": ["src/config"],
          "@config/*": ["src/config/*"],
        },
      },
    };

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    const result = readPathAliases(tempDir);

    expect(result["@config"]).toBe("src/config");
    expect(result["@config/"]).toBe("src/config/");
  });

  test("handles tsconfig with comments", () => {
    const tsconfigContent = `{
      // This is a comment
      "compilerOptions": {
        /* Multi-line
           comment */
        "baseUrl": ".",
        "paths": {
          "@core": ["src/core"]  // inline comment
        }
      }
    }`;

    fs.writeFileSync(path.join(tempDir, "tsconfig.json"), tsconfigContent);

    const result = readPathAliases(tempDir);

    expect(result["@core"]).toBe("src/core");
  });

  test("handles baseUrl other than root", () => {
    const tsconfig = {
      compilerOptions: {
        baseUrl: "src",
        paths: {
          "@core": ["core"],
        },
      },
    };

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    const result = readPathAliases(tempDir);

    expect(result["@core"]).toBe("src/core");
  });

  test("returns empty object when paths is empty", () => {
    const tsconfig = {
      compilerOptions: {
        baseUrl: ".",
        paths: {},
      },
    };

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    const result = readPathAliases(tempDir);
    expect(result).toEqual({});
  });

  test("returns empty object when paths is not defined", () => {
    const tsconfig = {
      compilerOptions: {
        baseUrl: ".",
      },
    };

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    const result = readPathAliases(tempDir);
    expect(result).toEqual({});
  });

  test("returns empty object when compilerOptions is not defined", () => {
    const tsconfig = {};

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    const result = readPathAliases(tempDir);
    expect(result).toEqual({});
  });

  test("returns empty object for invalid JSON", () => {
    fs.writeFileSync(path.join(tempDir, "tsconfig.json"), "{ invalid json");

    const result = readPathAliases(tempDir);
    expect(result).toEqual({});
  });

  test("skips path entries with empty targets", () => {
    const tsconfig = {
      compilerOptions: {
        baseUrl: ".",
        paths: {
          "@empty": [],
          "@valid": ["src/valid"],
        },
      },
    };

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    const result = readPathAliases(tempDir);

    expect(result["@empty"]).toBeUndefined();
    expect(result["@valid"]).toBe("src/valid");
  });
});

describe("readPathAliasesCached", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "tsconfig-cache-test-"));
    clearPathAliasCache();
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
    clearPathAliasCache();
  });

  test("caches results for same directory", () => {
    const tsconfig = {
      compilerOptions: {
        baseUrl: ".",
        paths: {
          "@test": ["src/test"],
        },
      },
    };

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    // First call
    const result1 = readPathAliasesCached(tempDir);
    expect(result1["@test"]).toBe("src/test");

    // Modify file
    const newTsconfig = {
      compilerOptions: {
        baseUrl: ".",
        paths: {
          "@modified": ["src/modified"],
        },
      },
    };
    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(newTsconfig),
    );

    // Second call should return cached result
    const result2 = readPathAliasesCached(tempDir);
    expect(result2["@test"]).toBe("src/test");
    expect(result2["@modified"]).toBeUndefined();
  });

  test("returns fresh results after cache clear", () => {
    const tsconfig = {
      compilerOptions: {
        baseUrl: ".",
        paths: {
          "@test": ["src/test"],
        },
      },
    };

    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(tsconfig),
    );

    // First call
    readPathAliasesCached(tempDir);

    // Modify file
    const newTsconfig = {
      compilerOptions: {
        baseUrl: ".",
        paths: {
          "@modified": ["src/modified"],
        },
      },
    };
    fs.writeFileSync(
      path.join(tempDir, "tsconfig.json"),
      JSON.stringify(newTsconfig),
    );

    // Clear cache
    clearPathAliasCache();

    // Should return fresh result
    const result = readPathAliasesCached(tempDir);
    expect(result["@modified"]).toBe("src/modified");
  });
});
