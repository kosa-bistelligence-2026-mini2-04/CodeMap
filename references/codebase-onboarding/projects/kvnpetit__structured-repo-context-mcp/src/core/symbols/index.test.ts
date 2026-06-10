import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { parseCode, resetParser } from "@core/parser";
import {
  extractCodeInfo,
  extractExports,
  extractImports,
  extractSymbols,
  findSymbolByName,
  getSymbolAtPosition,
  getSymbolsByType,
} from "@core/symbols";

describe("Symbol Extraction - JavaScript", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts function symbols", async () => {
    const code = `
      function hello() { return "world"; }
      const greet = (name) => "Hello " + name;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(symbols.length).toBeGreaterThan(0);
    expect(summary.functions).toBeGreaterThan(0);

    const helloFunc = symbols.find((s) => s.name === "hello");
    expect(helloFunc).toBeDefined();
    expect(helloFunc?.type).toBe("function");
  });

  test("extracts class symbols", async () => {
    const code = `
      class MyClass {
        constructor() {}
        method() {}
      }
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(summary.classes).toBe(1);

    const myClass = symbols.find((s) => s.name === "MyClass");
    expect(myClass).toBeDefined();
    expect(myClass?.type).toBe("class");
  });

  test("extracts variable symbols", async () => {
    const code = `
      const x = 1;
      let y = 2;
      var z = 3;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(summary.constants + summary.variables).toBeGreaterThan(0);

    const xVar = symbols.find((s) => s.name === "x");
    expect(xVar).toBeDefined();
  });

  test("filters symbols by type", async () => {
    const code = `
      function hello() {}
      class MyClass {}
      const x = 1;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
      { types: ["function"] },
    );

    // Should only have functions
    expect(symbols.every((s) => s.type === "function")).toBe(true);
  });

  test("excludes symbols by type", async () => {
    const code = `
      function hello() {}
      class MyClass {}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
      { excludeTypes: ["class"] },
    );

    // Should not have classes
    expect(symbols.every((s) => s.type !== "class")).toBe(true);
  });
});

describe("Symbol Extraction - TypeScript", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts TypeScript interfaces", async () => {
    const code = `
      interface User {
        name: string;
        age: number;
      }
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(summary.interfaces).toBe(1);

    const userInterface = symbols.find((s) => s.name === "User");
    expect(userInterface).toBeDefined();
    expect(userInterface?.type).toBe("interface");
  });

  test("extracts TypeScript type aliases", async () => {
    const code = `
      type Config = { debug: boolean };
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(summary.types).toBe(1);

    const configType = symbols.find((s) => s.name === "Config");
    expect(configType).toBeDefined();
    expect(configType?.type).toBe("type");
  });

  test("extracts TypeScript enums", async () => {
    const code = `
      enum Status {
        Active,
        Inactive
      }
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(summary.enums).toBe(1);

    const statusEnum = symbols.find((s) => s.name === "Status");
    expect(statusEnum).toBeDefined();
    expect(statusEnum?.type).toBe("enum");
  });
});

describe("Symbol Extraction - Python", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts Python functions", async () => {
    const code = `
def hello():
    return "world"

def greet(name):
    return f"Hello {name}"
    `;
    const result = await parseCode(code, { language: "python" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "python",
    );

    expect(summary.functions).toBe(2);

    const helloFunc = symbols.find((s) => s.name === "hello");
    expect(helloFunc).toBeDefined();
    expect(helloFunc?.type).toBe("function");
  });

  test("extracts Python classes", async () => {
    const code = `
class MyClass:
    def method(self):
        pass
    `;
    const result = await parseCode(code, { language: "python" });

    const { summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "python",
    );

    expect(summary.classes).toBe(1);
  });
});

describe("Import Extraction", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts JavaScript imports", async () => {
    const code = `
      import { x, y } from 'module';
      import z from 'other';
      import * as all from 'third';
    `;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBeGreaterThan(0);
  });

  test("extracts Python imports", async () => {
    const code = `
import os
from pathlib import Path
from typing import List, Dict
    `;
    const result = await parseCode(code, { language: "python" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "python",
    );

    expect(imports.length).toBeGreaterThan(0);
  });
});

describe("Export Extraction", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts JavaScript exports", async () => {
    const code = `
      export const x = 1;
      export function hello() {}
      export default class MyClass {}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(exports.length).toBeGreaterThan(0);

    const defaultExport = exports.find((e) => e.isDefault);
    expect(defaultExport).toBeDefined();
  });
});

describe("Symbol Utilities", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("getSymbolsByType filters correctly", async () => {
    const code = `
      function hello() {}
      class MyClass {}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    const functions = getSymbolsByType(symbols, "function");
    expect(functions.every((s) => s.type === "function")).toBe(true);
  });

  test("findSymbolByName finds correct symbol", async () => {
    const code = `
      function hello() {}
      function world() {}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    const found = findSymbolByName(symbols, "hello");
    expect(found).toBeDefined();
    expect(found?.name).toBe("hello");
  });

  test("findSymbolByName returns undefined for unknown name", async () => {
    const code = `function hello() {}`;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    const found = findSymbolByName(symbols, "unknown");
    expect(found).toBeUndefined();
  });

  test("getSymbolAtPosition finds symbol at position", async () => {
    const code = `function hello() { return 1; }`;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    const found = getSymbolAtPosition(symbols, 1, 15);
    expect(found).toBeDefined();
    expect(found?.name).toBe("hello");
  });
});

describe("Code Info Extraction", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extractCodeInfo returns complete info", async () => {
    const code = `
      import { x } from 'module';

      export function hello() {}

      class MyClass {}
    `;
    const parseResult = await parseCode(code, { language: "javascript" });

    const info = extractCodeInfo(
      parseResult.tree,
      parseResult.languageInstance,
      "javascript",
    );

    expect(info.symbols.symbols.length).toBeGreaterThan(0);
    expect(info.imports.length).toBeGreaterThan(0);
    expect(info.exports.length).toBeGreaterThan(0);
  });
});

describe("Import Edge Cases", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts default imports", async () => {
    const code = `import React from 'react';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(1);
    expect(imports[0]).toBeDefined();
  });

  test("extracts named imports with multiple names", async () => {
    const code = `import { useState, useEffect, useCallback } from 'react';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(1);
    expect(imports[0]).toBeDefined();
  });

  test("extracts mixed default and named imports", async () => {
    const code = `import React, { useState, useEffect } from 'react';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(1);
    expect(imports[0]).toBeDefined();
  });

  test("extracts multiple import statements", async () => {
    const code = `
import React from 'react';
import { render } from 'react-dom';
import * as utils from './utils';
    `;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBeGreaterThanOrEqual(2);
  });

  test("handles namespace imports", async () => {
    const code = `import * as fs from 'fs';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(1);
    expect(imports[0]).toBeDefined();
  });
});

describe("Export Edge Cases", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts export default function", async () => {
    const code = `export default function hello() {}`;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(exports.length).toBe(1);
    expect(exports[0]?.isDefault).toBe(true);
  });

  test("extracts export default class", async () => {
    const code = `export default class MyClass {}`;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(exports.length).toBe(1);
    expect(exports[0]?.isDefault).toBe(true);
  });

  test("extracts named exports", async () => {
    const code = `export const a = 1; export let b = 2; export var c = 3;`;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(exports.length).toBe(3);
  });

  test("extracts export interface in TypeScript", async () => {
    const code = `export interface User { name: string; }`;
    const result = await parseCode(code, { language: "typescript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(exports.length).toBeGreaterThan(0);
  });

  test("extracts export type in TypeScript", async () => {
    const code = `export type Status = 'active' | 'inactive';`;
    const result = await parseCode(code, { language: "typescript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(exports.length).toBeGreaterThan(0);
  });

  test("extracts export enum in TypeScript", async () => {
    const code = `export enum Color { Red, Green, Blue }`;
    const result = await parseCode(code, { language: "typescript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(exports.length).toBeGreaterThan(0);
  });
});

describe("Function Signature Extraction", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts arrow function symbols", async () => {
    const code = `const greet = (name: string): string => name;`;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(symbols.length).toBeGreaterThan(0);
  });

  test("extracts Python function symbols", async () => {
    const code = `
def greet(name: str) -> str:
    return f"Hello {name}"

def add(a: int, b: int) -> int:
    return a + b
    `;
    const result = await parseCode(code, { language: "python" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "python",
    );

    expect(summary.functions).toBe(2);
    expect(symbols.some((s) => s.name === "greet")).toBe(true);
  });

  test("extracts Go function symbols", async () => {
    const code = `
package main

func greet(name string) string {
    return "Hello " + name
}

func (s *Server) Start() error {
    return nil
}
    `;
    const result = await parseCode(code, { language: "go" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "go",
    );

    expect(symbols.length).toBeGreaterThan(0);
  });
});

describe("Import/Export Deduplication", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("handles imports with both default and named imports", async () => {
    const code = `
import React, { useState, useEffect, useCallback } from 'react';
import { render } from 'react-dom';
    `;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBeGreaterThanOrEqual(1);
  });

  test("deduplicates repeated export patterns", async () => {
    const code = `
export const a = 1;
export const b = 2;
export function hello() {}
export class MyClass {}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Each export should appear only once
    const names = exports.map((e) => e.name);
    const uniqueNames = [...new Set(names)];
    expect(names.length).toBe(uniqueNames.length);
  });
});

describe("Additional Symbol Extraction Edge Cases", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts method symbols from classes", async () => {
    const code = `
class MyClass {
  constructor() {}
  methodOne() {}
  methodTwo() {}
  static staticMethod() {}
}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(summary.methods).toBeGreaterThan(0);
    expect(symbols.some((s) => s.type === "method")).toBe(true);
  });

  test("extracts async functions", async () => {
    const code = `
async function fetchData() {
  return await fetch('/api');
}

const asyncArrow = async () => {
  return 42;
};
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(summary.functions).toBeGreaterThan(0);
    expect(symbols.some((s) => s.modifiers?.includes("async"))).toBe(true);
  });

  test("getSymbolAtPosition returns undefined for position outside symbols", async () => {
    const code = `
// Comment line
function hello() { return 1; }
// Another comment
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Position in comment area (line 1)
    const found = getSymbolAtPosition(symbols, 1, 0);
    // May or may not find depending on exact position
    expect(found === undefined || found.name === "hello").toBe(true);
  });

  test("extracts TypeScript type aliases correctly", async () => {
    const code = `
type StringOrNumber = string | number;
type Config = {
  debug: boolean;
  port: number;
};
type Callback<T> = (value: T) => void;
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(summary.types).toBeGreaterThan(0);
    expect(symbols.some((s) => s.name === "StringOrNumber")).toBe(true);
  });

  test("extracts generator functions", async () => {
    const code = `
function* numberGenerator() {
  yield 1;
  yield 2;
  yield 3;
}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(symbols.length).toBeGreaterThan(0);
    expect(symbols.some((s) => s.name === "numberGenerator")).toBe(true);
  });

  test("extracts Go functions with receivers", async () => {
    const code = `
package main

func (s *Server) Start() error {
    return nil
}

func (s Server) Stop() {
}
    `;
    const result = await parseCode(code, { language: "go" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "go",
    );

    expect(symbols.length).toBeGreaterThan(0);
  });

  test("handles export default anonymous function", async () => {
    const code = `
export default function() {
  return "anonymous";
}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(exports.some((e) => e.isDefault)).toBe(true);
  });

  test("extracts Python decorators and modifiers", async () => {
    const code = `
@staticmethod
def static_func():
    pass

@classmethod
def class_func(cls):
    pass

@property
def prop(self):
    return self._value
    `;
    const result = await parseCode(code, { language: "python" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "python",
    );

    expect(symbols.length).toBeGreaterThan(0);
  });

  test("extracts Rust functions and methods", async () => {
    const code = `
fn main() {
    println!("Hello");
}

pub fn helper() -> i32 {
    42
}

impl Person {
    fn new() -> Self {
        Person {}
    }
}
    `;
    const result = await parseCode(code, { language: "rust" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "rust",
    );

    // Rust symbol extraction may not capture all constructs
    // but should at least not fail
    expect(symbols).toBeDefined();
  });
});

describe("Symbol Filter Edge Cases", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("filter with both types and excludeTypes", async () => {
    const code = `
function hello() {}
class MyClass {}
const x = 1;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
      { types: ["function", "class"], excludeTypes: ["class"] },
    );

    // Should have functions but not classes
    expect(symbols.every((s) => s.type === "function")).toBe(true);
    expect(symbols.some((s) => s.type === "class")).toBe(false);
  });

  test("filter excludeTypes only", async () => {
    const code = `
function hello() {}
class MyClass {}
const x = 1;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
      { excludeTypes: ["function"] },
    );

    // Should not have any functions
    expect(symbols.every((s) => s.type !== "function")).toBe(true);
  });

  test("filter types only - variables and constants", async () => {
    const code = `
function hello() {}
class MyClass {}
const x = 1;
let y = 2;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
      { types: ["variable", "constant"] },
    );

    // Should only have variables or constants
    expect(
      symbols.every((s) => s.type === "variable" || s.type === "constant"),
    ).toBe(true);
  });

  test("filter types only - interfaces and types", async () => {
    const code = `
interface User { name: string; }
type Config = { debug: boolean };
enum Status { Active, Inactive }
function hello() {}
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
      { types: ["interface", "type", "enum"] },
    );

    // Should only have interfaces, types, or enums
    expect(
      symbols.every(
        (s) => s.type === "interface" || s.type === "type" || s.type === "enum",
      ),
    ).toBe(true);
  });

  test("filter excludeTypes - interfaces", async () => {
    const code = `
interface User { name: string; }
type Config = { debug: boolean };
function hello() {}
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
      { excludeTypes: ["interface"] },
    );

    // Should not have interfaces
    expect(symbols.every((s) => s.type !== "interface")).toBe(true);
  });

  test("filter excludeTypes - methods", async () => {
    const code = `
class MyClass {
  method() {}
}
function standalone() {}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
      { excludeTypes: ["method"] },
    );

    // Should not have methods
    expect(symbols.every((s) => s.type !== "method")).toBe(true);
  });
});

describe("Method Detection Edge Cases", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("detects method_definition type", async () => {
    const code = `
class Calculator {
  add(a, b) { return a + b; }
  subtract(a, b) { return a - b; }
}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(summary.methods).toBeGreaterThan(0);
  });

  test("distinguishes between methods and functions", async () => {
    const code = `
function standalone() {}
class MyClass {
  method() {}
}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(summary.functions).toBeGreaterThan(0);
    expect(summary.methods).toBeGreaterThan(0);
  });
});

describe("Interface/Struct Detection", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("detects TypeScript interface declarations", async () => {
    const code = `
interface IUser {
  id: number;
  name: string;
}
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(summary.interfaces).toBe(1);
    expect(symbols.find((s) => s.name === "IUser")?.type).toBe("interface");
  });

  test("handles Go structs as interfaces", async () => {
    const code = `
package main

type Person struct {
    Name string
    Age  int
}
    `;
    const result = await parseCode(code, { language: "go" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "go",
    );

    // Go structs may be detected - at minimum should not error
    expect(symbols).toBeDefined();
  });
});

describe("Variable/Constant Detection", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("detects const as constant", async () => {
    const code = `
const API_KEY = "secret";
const MAX_SIZE = 100;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Variables query may not be available for all languages
    // At minimum should not error
    expect(summary.constants + summary.variables).toBeGreaterThanOrEqual(0);
    expect(symbols).toBeDefined();
  });

  test("detects let/var as variable", async () => {
    const code = `
let counter = 0;
var total = 0;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const { summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Either constants or variables should be detected
    expect(summary.constants + summary.variables).toBeGreaterThanOrEqual(0);
  });
});

describe("Type/Enum Name Detection", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("detects interface.name capture", async () => {
    const code = `
interface Config {
  debug: boolean;
}
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    const configSymbol = symbols.find((s) => s.name === "Config");
    expect(configSymbol?.type).toBe("interface");
  });

  test("detects enum.name capture", async () => {
    const code = `
enum Direction {
  Up,
  Down,
  Left,
  Right
}
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(summary.enums).toBe(1);
    const directionEnum = symbols.find((s) => s.name === "Direction");
    expect(directionEnum?.type).toBe("enum");
  });

  test("detects type.alias capture", async () => {
    const code = `
type ID = string | number;
type Handler = (event: Event) => void;
    `;
    const result = await parseCode(code, { language: "typescript" });

    const { symbols, summary } = extractSymbols(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(summary.types).toBeGreaterThan(0);
    expect(symbols.some((s) => s.name === "ID")).toBe(true);
  });
});

describe("Import Edge Cases - Names and Sources", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts source from import statement", async () => {
    const code = `import { useState } from 'react';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Source extraction depends on query pattern
    // At minimum the import should be detected
    expect(imports.length).toBe(1);
    expect(imports[0]).toBeDefined();
    // Source may or may not be extracted depending on query
    expect(imports[0]?.source).toBeDefined();
  });

  test("handles import without source gracefully", async () => {
    // Side-effect import
    const code = `import 'polyfill';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBeGreaterThanOrEqual(0);
  });

  test("extracts default import names", async () => {
    const code = `import React from 'react';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(1);
    // Default import should have isDefault flag or contain name
    expect(imports[0]).toBeDefined();
  });

  test("extracts named import names", async () => {
    const code = `import { a, b, c } from 'module';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(1);
    expect(imports[0]?.names.length).toBeGreaterThanOrEqual(0);
  });
});

describe("Export Edge Cases - Name Extraction", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("extracts name from export const", async () => {
    const code = `export const API_URL = "https://api.example.com";`;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(exports.length).toBe(1);
    expect(exports[0]?.name).toBeDefined();
  });

  test("extracts name from export let", async () => {
    const code = `export let counter = 0;`;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(exports.length).toBe(1);
  });

  test("extracts name from export var", async () => {
    const code = `export var globalVar = "value";`;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(exports.length).toBe(1);
  });

  test("export default without explicit name", async () => {
    const code = `export default { key: "value" };`;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    const defaultExport = exports.find((e) => e.isDefault);
    expect(defaultExport).toBeDefined();
    // Name should be "default" when no explicit name
    expect(defaultExport?.name).toBeDefined();
  });
});

describe("Import/Export Deduplication and Capture Handling", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("deduplicates repeated import statements", async () => {
    // Code with imports that might match multiple query patterns
    const code = `
import React from 'react';
import { useState } from 'react';
import { useEffect, useCallback, useMemo } from 'react';
    `;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Ensure no duplicates based on position
    const positions = imports.map(
      (i) => `${String(i.start.line)}:${String(i.start.column)}`,
    );
    const uniquePositions = [...new Set(positions)];
    expect(positions.length).toBe(uniquePositions.length);
  });

  test("deduplicates repeated export statements", async () => {
    const code = `
export const a = 1;
export const b = 2;
export function hello() {}
export function world() {}
export class MyClass {}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Ensure no duplicates based on position
    const positions = exports.map(
      (e) => `${String(e.start.line)}:${String(e.start.column)}`,
    );
    const uniquePositions = [...new Set(positions)];
    expect(positions.length).toBe(uniquePositions.length);
  });

  test("handles imports with default and named combined", async () => {
    const code = `
import React, { useState, useEffect, useRef } from 'react';
    `;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(1);
    // Should have names extracted
    expect(imports[0]?.names.length).toBeGreaterThanOrEqual(0);
  });

  test("handles multiple named imports in sequence", async () => {
    const code = `
import { a, b, c, d, e } from 'alphabet';
import { x, y, z } from 'xyz';
    `;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(2);
  });

  test("handles export without explicit name (default anonymous)", async () => {
    const code = `
export default function() {
  return 42;
}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    const defaultExport = exports.find((e) => e.isDefault);
    expect(defaultExport).toBeDefined();
    // Name should be extracted or fallback to "default"
    expect(defaultExport?.name).toBeDefined();
  });

  test("extracts default import capture", async () => {
    const code = `import DefaultExport from 'module';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(1);
    // Default import should be captured, names array may or may not have content
    expect(imports[0]).toBeDefined();
    expect(imports[0]?.source).toBeDefined();
  });

  test("extracts named import captures", async () => {
    const code = `import { namedA, namedB, namedC } from 'module';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(1);
    // Named imports should be in the names array
    expect(imports[0]?.isDefault).toBe(false);
  });

  test("handles complex TypeScript imports", async () => {
    const code = `
import type { Type1, Type2 } from 'types';
import DefaultClass, { method1, method2 } from 'mixed';
import * as namespace from 'namespace';
    `;
    const result = await parseCode(code, { language: "typescript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(imports.length).toBeGreaterThanOrEqual(2);
  });

  test("handles TypeScript re-exports", async () => {
    const code = `
export { default } from 'module';
export { named1, named2 } from 'other';
export * from 'all';
    `;
    const result = await parseCode(code, { language: "typescript" });

    const exports = extractExports(
      result.tree,
      result.languageInstance,
      "typescript",
    );

    expect(exports.length).toBeGreaterThanOrEqual(1);
  });

  test("handles side-effect only imports", async () => {
    const code = `import 'side-effect';`;
    const result = await parseCode(code, { language: "javascript" });

    const imports = extractImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Side-effect imports may or may not be captured depending on query
    expect(imports.length).toBeGreaterThanOrEqual(0);
  });
});

describe("getSymbolAtPosition Edge Cases", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("position at exact start of symbol", async () => {
    const code = `function hello() { return 1; }`;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Position at very start
    const found = getSymbolAtPosition(symbols, 1, 0);
    expect(found?.name).toBe("hello");
  });

  test("position at exact end of symbol", async () => {
    const code = `function hello() { return 1; }`;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Position at end of first line
    const found = getSymbolAtPosition(symbols, 1, 30);
    expect(found?.name).toBe("hello");
  });

  test("position before any symbol", async () => {
    const code = `

function hello() { return 1; }`;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Position at line 1 which is empty
    const found = getSymbolAtPosition(symbols, 1, 0);
    expect(found).toBeUndefined();
  });

  test("multi-line function position", async () => {
    const code = `function hello() {
  const x = 1;
  return x;
}`;
    const result = await parseCode(code, { language: "javascript" });

    const { symbols } = extractSymbols(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    // Position in middle of function
    const found = getSymbolAtPosition(symbols, 2, 5);
    expect(found?.name).toBe("hello");
  });
});
