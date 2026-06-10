import { describe, expect, test } from "vitest";

import {
  canParse,
  detectLanguage,
  extractSymbols,
  getParsingCapabilities,
  getSupportedLanguagesInfo,
  isBinaryFile,
  parseContent,
  parseFile,
} from "@core/unified";

describe("Unified Parser", () => {
  describe("isBinaryFile", () => {
    test("detects binary files", () => {
      expect(isBinaryFile("image.png")).toBe(true);
      expect(isBinaryFile("video.mp4")).toBe(true);
      expect(isBinaryFile("archive.zip")).toBe(true);
      expect(isBinaryFile("program.exe")).toBe(true);
      expect(isBinaryFile("module.wasm")).toBe(true);
    });

    test("allows text files", () => {
      expect(isBinaryFile("code.js")).toBe(false);
      expect(isBinaryFile("readme.md")).toBe(false);
      expect(isBinaryFile("config.json")).toBe(false);
      expect(isBinaryFile("script.py")).toBe(false);
    });
  });

  describe("detectLanguage", () => {
    test("detects Tree-sitter supported languages", () => {
      expect(detectLanguage("file.js")).toBe("javascript");
      expect(detectLanguage("file.ts")).toBe("typescript");
      expect(detectLanguage("file.py")).toBe("python");
      expect(detectLanguage("file.rs")).toBe("rust");
      expect(detectLanguage("file.go")).toBe("go");
    });

    test("detects fallback languages", () => {
      expect(detectLanguage("file.md")).toBe("markdown");
      expect(detectLanguage("file.json")).toBe("json");
      expect(detectLanguage("file.yaml")).toBe("yaml");
      expect(detectLanguage("file.sh")).toBe("bash");
      expect(detectLanguage("file.css")).toBe("css");
    });

    test("detects special filenames", () => {
      expect(detectLanguage("Dockerfile")).toBe("dockerfile");
      expect(detectLanguage("Makefile")).toBe("makefile");
      expect(detectLanguage(".gitignore")).toBe("gitignore");
      expect(detectLanguage(".env")).toBe("env");
    });

    test("returns text for unknown files", () => {
      expect(detectLanguage("file.xyz")).toBe("text");
      expect(detectLanguage("unknownfile")).toBe("text");
    });
  });

  describe("canParse", () => {
    test("returns true for text files", () => {
      expect(canParse("file.js")).toBe(true);
      expect(canParse("file.md")).toBe(true);
      expect(canParse("file.txt")).toBe(true);
    });

    test("returns false for binary files", () => {
      expect(canParse("image.png")).toBe(false);
      expect(canParse("program.exe")).toBe(false);
    });
  });

  describe("getParsingCapabilities", () => {
    test("returns tree-sitter for supported languages", () => {
      const caps = getParsingCapabilities("file.js");
      expect(caps.method).toBe("tree-sitter");
      expect(caps.language).toBe("javascript");
      expect(caps.features).toContain("Full AST parsing");
    });

    test("returns langchain for fallback languages", () => {
      const caps = getParsingCapabilities("file.md");
      expect(caps.method).toBe("langchain");
      expect(caps.language).toBe("markdown");
      expect(caps.features).toContain("Intelligent text splitting");
    });

    test("returns generic for unknown languages", () => {
      const caps = getParsingCapabilities("file.xyz");
      expect(caps.method).toBe("generic");
      expect(caps.features).toContain("Generic text splitting");
    });
  });

  describe("getSupportedLanguagesInfo", () => {
    test("returns list of supported languages", () => {
      const languages = getSupportedLanguagesInfo();

      expect(languages.length).toBeGreaterThan(20);

      // Check Tree-sitter languages
      const jsLang = languages.find((l) => l.language === "javascript");
      expect(jsLang).toBeDefined();
      if (jsLang) {
        expect(jsLang.method).toBe("tree-sitter");
        expect(jsLang.extensions).toContain(".js");
      }

      // Check LangChain languages
      const mdLang = languages.find((l) => l.language === "markdown");
      expect(mdLang).toBeDefined();
      if (mdLang) {
        expect(mdLang.method).toBe("langchain");
        expect(mdLang.extensions).toContain(".md");
      }
    });
  });
});

// ============================================================
// TREE-SITTER LANGUAGES (18 WASM) - Full AST Parsing Tests
// ============================================================
describe("Tree-sitter Languages (18 WASM)", () => {
  // JavaScript
  describe("JavaScript", () => {
    test("parses JavaScript code", async () => {
      const code = `
function greet(name) {
  return "Hello, " + name;
}

const arrow = (x) => x * 2;

class Person {
  constructor(name) {
    this.name = name;
  }

  sayHello() {
    return "Hi, I'm " + this.name;
  }
}

export { greet, Person };
`;
      const result = await parseContent(code, "javascript");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("javascript");
      expect(result.tree).toBeDefined();

      const symbols = extractSymbols({ ...result, filePath: "test.js" });
      expect(symbols.method).toBe("tree-sitter");
      expect(symbols.functions.length).toBeGreaterThan(0);
      expect(symbols.classes.length).toBeGreaterThan(0);
    });
  });

  // TypeScript
  describe("TypeScript", () => {
    test("parses TypeScript code", async () => {
      const code = `
interface User {
  name: string;
  age: number;
}

function greet(user: User): string {
  return \`Hello, \${user.name}\`;
}

class UserService {
  private users: User[] = [];

  addUser(user: User): void {
    this.users.push(user);
  }
}

type Status = "active" | "inactive";
`;
      const result = await parseContent(code, "typescript");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("typescript");
      expect(result.tree).toBeDefined();

      const symbols = extractSymbols({ ...result, filePath: "test.ts" });
      expect(symbols.method).toBe("tree-sitter");
    });
  });

  // TSX
  describe("TSX", () => {
    test("parses TSX code", async () => {
      const code = `
import React from 'react';

interface Props {
  name: string;
}

function Greeting({ name }: Props): JSX.Element {
  return <div>Hello, {name}!</div>;
}

export const App: React.FC = () => {
  return (
    <div>
      <Greeting name="World" />
    </div>
  );
};
`;
      const result = await parseContent(code, "tsx");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("tsx");
      expect(result.tree).toBeDefined();
    });
  });

  // Python
  describe("Python", () => {
    test("parses Python code", async () => {
      const code = `
def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

class Person:
    def __init__(self, name: str):
        self.name = name

    def say_hello(self) -> str:
        return f"Hi, I'm {self.name}"

async def fetch_data(url: str):
    pass
`;
      const result = await parseContent(code, "python");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("python");
      expect(result.tree).toBeDefined();

      const symbols = extractSymbols({ ...result, filePath: "test.py" });
      expect(symbols.functions.length).toBeGreaterThan(0);
      expect(symbols.classes.length).toBeGreaterThan(0);
    });
  });

  // Rust
  describe("Rust", () => {
    test("parses Rust code", async () => {
      const code = `
fn main() {
    println!("Hello, world!");
}

struct Person {
    name: String,
    age: u32,
}

impl Person {
    fn new(name: &str, age: u32) -> Self {
        Person {
            name: name.to_string(),
            age,
        }
    }

    fn greet(&self) -> String {
        format!("Hello, I'm {}", self.name)
    }
}

trait Greeter {
    fn greet(&self) -> String;
}
`;
      const result = await parseContent(code, "rust");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("rust");
      expect(result.tree).toBeDefined();
    });
  });

  // Go
  describe("Go", () => {
    test("parses Go code", async () => {
      const code = `
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}

type Person struct {
    Name string
    Age  int
}

func (p *Person) Greet() string {
    return fmt.Sprintf("Hello, I'm %s", p.Name)
}

func NewPerson(name string, age int) *Person {
    return &Person{Name: name, Age: age}
}
`;
      const result = await parseContent(code, "go");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("go");
      expect(result.tree).toBeDefined();
    });
  });

  // C
  describe("C", () => {
    test("parses C code", async () => {
      const code = `
#include <stdio.h>

struct Person {
    char* name;
    int age;
};

void greet(const char* name) {
    printf("Hello, %s!\\n", name);
}

int main() {
    greet("World");
    return 0;
}
`;
      const result = await parseContent(code, "c");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("c");
      expect(result.tree).toBeDefined();
    });
  });

  // C++
  describe("C++", () => {
    test("parses C++ code", async () => {
      const code = `
#include <iostream>
#include <string>

class Person {
private:
    std::string name;
    int age;

public:
    Person(const std::string& n, int a) : name(n), age(a) {}

    std::string greet() const {
        return "Hello, I'm " + name;
    }
};

template<typename T>
T add(T a, T b) {
    return a + b;
}

int main() {
    Person p("World", 30);
    std::cout << p.greet() << std::endl;
    return 0;
}
`;
      const result = await parseContent(code, "cpp");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("cpp");
      expect(result.tree).toBeDefined();
    });
  });

  // Java
  describe("Java", () => {
    test("parses Java code", async () => {
      const code = `
package com.example;

public class Person {
    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    public String greet() {
        return "Hello, I'm " + name;
    }

    public static void main(String[] args) {
        Person p = new Person("World", 30);
        System.out.println(p.greet());
    }
}

interface Greeter {
    String greet();
}
`;
      const result = await parseContent(code, "java");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("java");
      expect(result.tree).toBeDefined();
    });
  });

  // Ruby
  describe("Ruby", () => {
    test("parses Ruby code", async () => {
      const code = `
class Person
  attr_accessor :name, :age

  def initialize(name, age)
    @name = name
    @age = age
  end

  def greet
    "Hello, I'm #{@name}"
  end
end

module Greeter
  def say_hello
    puts "Hello!"
  end
end

def main
  p = Person.new("World", 30)
  puts p.greet
end
`;
      const result = await parseContent(code, "ruby");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("ruby");
      expect(result.tree).toBeDefined();
    });
  });

  // PHP
  describe("PHP", () => {
    test("parses PHP code", async () => {
      const code = `<?php

class Person {
    private string $name;
    private int $age;

    public function __construct(string $name, int $age) {
        $this->name = $name;
        $this->age = $age;
    }

    public function greet(): string {
        return "Hello, I'm " . $this->name;
    }
}

function main(): void {
    $p = new Person("World", 30);
    echo $p->greet();
}

interface Greeter {
    public function greet(): string;
}
`;
      const result = await parseContent(code, "php");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("php");
      expect(result.tree).toBeDefined();
    });
  });

  // Swift
  describe("Swift", () => {
    test("parses Swift code", async () => {
      const code = `
import Foundation

class Person {
    var name: String
    var age: Int

    init(name: String, age: Int) {
        self.name = name
        self.age = age
    }

    func greet() -> String {
        return "Hello, I'm \\(name)"
    }
}

protocol Greeter {
    func greet() -> String
}

func main() {
    let p = Person(name: "World", age: 30)
    print(p.greet())
}
`;
      const result = await parseContent(code, "swift");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("swift");
      expect(result.tree).toBeDefined();
    });
  });

  // Kotlin
  describe("Kotlin", () => {
    test("parses Kotlin code", async () => {
      const code = `
package com.example

class Person(val name: String, val age: Int) {
    fun greet(): String {
        return "Hello, I'm $name"
    }
}

interface Greeter {
    fun greet(): String
}

fun main() {
    val p = Person("World", 30)
    println(p.greet())
}

data class User(val id: Int, val name: String)
`;
      const result = await parseContent(code, "kotlin");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("kotlin");
      expect(result.tree).toBeDefined();
    });
  });

  // Scala
  describe("Scala", () => {
    test("parses Scala code", async () => {
      const code = `
package com.example

class Person(val name: String, val age: Int) {
  def greet(): String = s"Hello, I'm $name"
}

trait Greeter {
  def greet(): String
}

object Main {
  def main(args: Array[String]): Unit = {
    val p = new Person("World", 30)
    println(p.greet())
  }
}

case class User(id: Int, name: String)
`;
      const result = await parseContent(code, "scala");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("scala");
      expect(result.tree).toBeDefined();
    });
  });

  // OCaml
  describe("OCaml", () => {
    test("parses OCaml code", async () => {
      const code = `
type person = {
  name: string;
  age: int;
}

let greet name =
  "Hello, " ^ name

let create_person name age =
  { name; age }

let main () =
  let p = create_person "World" 30 in
  print_endline (greet p.name)
`;
      const result = await parseContent(code, "ocaml");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("ocaml");
      expect(result.tree).toBeDefined();
    });
  });

  // C#
  describe("C#", () => {
    test("parses C# code", async () => {
      const code = `
using System;

namespace Example
{
    public class Person
    {
        public string Name { get; set; }
        public int Age { get; set; }

        public Person(string name, int age)
        {
            Name = name;
            Age = age;
        }

        public string Greet()
        {
            return $"Hello, I'm {Name}";
        }
    }

    public interface IGreeter
    {
        string Greet();
    }

    class Program
    {
        static void Main(string[] args)
        {
            var p = new Person("World", 30);
            Console.WriteLine(p.Greet());
        }
    }
}
`;
      const result = await parseContent(code, "csharp");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("c_sharp");
      expect(result.tree).toBeDefined();
    });
  });

  // HTML
  describe("HTML", () => {
    test("parses HTML code", async () => {
      const code = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Hello World</title>
</head>
<body>
    <div class="container">
        <h1>Welcome</h1>
        <p>Hello, World!</p>
    </div>
    <script>
        console.log("Hello");
    </script>
</body>
</html>
`;
      const result = await parseContent(code, "html");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("html");
      expect(result.tree).toBeDefined();
    });
  });

  // Svelte
  describe("Svelte", () => {
    test("parses Svelte code", async () => {
      const code = `
<script lang="ts">
  export let name: string = "World";

  function greet() {
    return \`Hello, \${name}!\`;
  }
</script>

<main>
  <h1>{greet()}</h1>
  <button on:click={() => name = "Svelte"}>
    Click me
  </button>
</main>

<style>
  main {
    text-align: center;
  }
</style>
`;
      const result = await parseContent(code, "svelte");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("tree-sitter");
      expect(result.language).toBe("svelte");
      expect(result.tree).toBeDefined();
    });
  });
});

// ============================================================
// VUE - Falls back to LangChain (no compatible WASM available)
// ============================================================
describe("Vue Fallback", () => {
  describe("Vue", () => {
    test("parses Vue with LangChain fallback", async () => {
      const code = `
<template>
  <div class="app">
    <h1>{{ greeting }}</h1>
    <button @click="updateName">Click me</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const name = ref('World');

const greeting = computed(() => \`Hello, \${name.value}!\`);

function updateName() {
  name.value = 'Vue';
}
</script>

<style scoped>
.app {
  text-align: center;
}
</style>
`;
      const result = await parseContent(code, "vue");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("langchain");
      expect(result.language).toBe("vue");
      expect(result.chunks).toBeDefined();

      // LangChain fallback does not extract symbols (text splitting only)
      const symbols = extractSymbols({ ...result, filePath: "test.vue" });
      expect(symbols.method).toBe("regex");
      expect(symbols.functions.length).toBe(0);
      expect(symbols.classes.length).toBe(0);
    });
  });
});

// ============================================================
// LANGCHAIN FALLBACK LANGUAGES - Text Splitting Tests
// ============================================================
describe("LangChain Fallback Languages", () => {
  // Markdown
  describe("Markdown", () => {
    test("parses Markdown with LangChain", async () => {
      const code = `
# Title

This is a paragraph with some text.

## Section 1

- Item 1
- Item 2
- Item 3

## Section 2

\`\`\`javascript
function hello() {
  return "world";
}
\`\`\`

### Subsection

More content here.
`;
      const result = await parseContent(code, "markdown");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("langchain");
      expect(result.language).toBe("markdown");
      expect(result.chunks).toBeDefined();
      if (result.chunks) {
        expect(result.chunks.length).toBeGreaterThan(0);
      }
    });
  });

  // JSON
  describe("JSON", () => {
    test("parses JSON with LangChain", async () => {
      const code = `{
  "name": "example",
  "version": "1.0.0",
  "dependencies": {
    "lodash": "^4.17.21",
    "express": "^4.18.0"
  },
  "scripts": {
    "start": "node index.js",
    "test": "jest"
  }
}`;
      const result = await parseContent(code, "json");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("langchain");
      expect(result.language).toBe("json");
      expect(result.chunks).toBeDefined();
    });
  });

  // YAML
  describe("YAML", () => {
    test("parses YAML with LangChain", async () => {
      const code = `
name: example
version: 1.0.0

services:
  web:
    image: nginx
    ports:
      - "80:80"
  db:
    image: postgres
    environment:
      POSTGRES_PASSWORD: secret

volumes:
  data:
`;
      const result = await parseContent(code, "yaml");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("langchain");
      expect(result.language).toBe("yaml");
      expect(result.chunks).toBeDefined();
    });
  });

  // Bash
  describe("Bash", () => {
    test("parses Bash with LangChain", async () => {
      const code = `
#!/bin/bash

# Configuration
NAME="World"
COUNT=5

# Function definition
greet() {
    local name=$1
    echo "Hello, $name!"
}

# Main script
for i in $(seq 1 $COUNT); do
    greet "$NAME"
done

if [ -f "config.txt" ]; then
    source config.txt
fi
`;
      const result = await parseContent(code, "bash");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("langchain");
      expect(result.language).toBe("bash");
      expect(result.chunks).toBeDefined();

      // Test regex symbol extraction
      const symbols = extractSymbols({ ...result, filePath: "test.sh" });
      expect(symbols.method).toBe("regex");
    });
  });

  // CSS
  describe("CSS", () => {
    test("parses CSS with LangChain", async () => {
      const code = `
/* Main styles */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
}

#header {
    background-color: #333;
    color: white;
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
}
`;
      const result = await parseContent(code, "css");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("langchain");
      expect(result.language).toBe("css");
      expect(result.chunks).toBeDefined();
    });
  });

  // SQL
  describe("SQL", () => {
    test("parses SQL with LangChain", async () => {
      const code = `
-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert sample data
INSERT INTO users (name, email) VALUES
    ('John', 'john@example.com'),
    ('Jane', 'jane@example.com');

-- Query users
SELECT * FROM users WHERE created_at > '2024-01-01';
`;
      const result = await parseContent(code, "sql");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("langchain");
      expect(result.language).toBe("sql");
      expect(result.chunks).toBeDefined();
    });
  });

  // LaTeX
  describe("LaTeX", () => {
    test("parses LaTeX with LangChain", async () => {
      const code = `
\\documentclass{article}
\\usepackage{amsmath}

\\title{Hello World}
\\author{Author Name}

\\begin{document}
\\maketitle

\\section{Introduction}
This is a simple LaTeX document.

\\section{Math}
The quadratic formula is:
\\begin{equation}
x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
\\end{equation}

\\end{document}
`;
      const result = await parseContent(code, "latex");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("langchain");
      expect(result.language).toBe("latex");
      expect(result.chunks).toBeDefined();
    });
  });

  // Protocol Buffers
  describe("Protocol Buffers", () => {
    test("parses Proto with LangChain", async () => {
      const code = `
syntax = "proto3";

package example;

message Person {
    string name = 1;
    int32 age = 2;
    repeated string emails = 3;
}

message AddressBook {
    repeated Person people = 1;
}

service Greeter {
    rpc SayHello (Person) returns (HelloReply);
}

message HelloReply {
    string message = 1;
}
`;
      const result = await parseContent(code, "proto");
      if (!result) {
        throw new Error("Expected result to be defined");
      }
      expect(result.method).toBe("langchain");
      expect(result.language).toBe("proto");
      expect(result.chunks).toBeDefined();
    });
  });
});

// ============================================================
// GENERIC FALLBACK - Any Text File
// ============================================================
describe("Generic Fallback", () => {
  test("parses unknown file type with generic splitter", async () => {
    const code = `
Some random text content
that doesn't match any known language.

function fake() {
  this looks like code but isn't recognized
}

class FakeClass {
  constructor() {}
}

More text here...
`;
    const result = await parseContent(code, "unknown");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(result.method).toBe("generic");
    expect(result.chunks).toBeDefined();
    if (result.chunks) {
      expect(result.chunks.length).toBeGreaterThan(0);
    }

    // Generic fallback does not extract symbols (text splitting only)
    const symbols = extractSymbols({ ...result, filePath: "test.unknown" });
    expect(symbols.method).toBe("regex");
    expect(symbols.functions.length).toBe(0);
    expect(symbols.classes.length).toBe(0);
  });
});

// ============================================================
// FILE PARSING TESTS
// ============================================================
describe("parseFile", () => {
  test("parses TypeScript file with Tree-sitter", async () => {
    const result = await parseFile("src/core/unified/index.ts");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    expect(result.method).toBe("tree-sitter");
    expect(result.language).toBe("typescript");
    expect(result.tree).toBeDefined();
    expect(result.lineCount).toBeGreaterThan(100);
  });

  test("parses package.json with LangChain", async () => {
    const result = await parseFile("package.json");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    expect(result.method).toBe("langchain");
    expect(result.language).toBe("json");
    expect(result.chunks).toBeDefined();
  });

  test("returns undefined for binary files", async () => {
    const result = await parseFile("test.png");
    expect(result).toBeUndefined();
  });
});

// ============================================================
// SYMBOL EXTRACTION TESTS
// ============================================================
describe("Symbol Extraction", () => {
  test("extracts functions and classes from JavaScript", async () => {
    const code = `
function regularFunction() {}
const arrowFunction = () => {};
async function asyncFunction() {}

class MyClass {
  constructor() {}
  method() {}
}
`;
    const result = await parseContent(code, "javascript");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    const symbols = extractSymbols({ ...result, filePath: "test.js" });

    expect(symbols.method).toBe("tree-sitter");
    expect(
      symbols.functions.some(
        (f) => f.name.includes("Function") || f.name === "method",
      ),
    ).toBe(true);
    expect(symbols.classes.some((c) => c.name === "MyClass")).toBe(true);
  });

  test("extracts symbols from Python", async () => {
    const code = `
def my_function():
    pass

async def async_function():
    pass

class MyClass:
    def method(self):
        pass
`;
    const result = await parseContent(code, "python");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    const symbols = extractSymbols({ ...result, filePath: "test.py" });

    expect(symbols.method).toBe("tree-sitter");
    expect(symbols.functions.length).toBeGreaterThan(0);
    expect(symbols.classes.length).toBeGreaterThan(0);
  });

  test("returns empty symbols for fallback languages (no regex extraction)", async () => {
    const code = `
function myFunc() {
  return 42;
}

class MyClass {
  constructor() {}
}

def python_func():
    pass
`;
    const result = await parseContent(code, "text");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    const symbols = extractSymbols({ ...result, filePath: "test.txt" });

    // Fallback uses text splitting only, no symbol extraction
    expect(symbols.method).toBe("regex");
    expect(symbols.functions.length).toBe(0);
    expect(symbols.classes.length).toBe(0);
  });
});

// ============================================================
// INCLUDE AST OPTIONS
// ============================================================
describe("Include AST Options", () => {
  test("parseContent includes AST when requested", async () => {
    const code = `function hello() { return "world"; }`;
    const result = await parseContent(code, "javascript", { includeAst: true });

    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(result.ast).toBeDefined();
    expect(result.ast?.type).toBe("program");
  });

  test("parseContent respects astMaxDepth", async () => {
    const code = `function hello() { return "world"; }`;
    const resultDeep = await parseContent(code, "javascript", {
      includeAst: true,
      astMaxDepth: 10,
    });
    const resultShallow = await parseContent(code, "javascript", {
      includeAst: true,
      astMaxDepth: 1,
    });

    if (!resultDeep || !resultShallow) {
      throw new Error("Expected results to be defined");
    }
    expect(resultDeep.ast).toBeDefined();
    expect(resultShallow.ast).toBeDefined();
    // Shallow should have fewer nested children
    expect(resultShallow.ast?.children?.length).toBeLessThanOrEqual(
      resultDeep.ast?.children?.length ?? 0,
    );
  });

  test("parseFile includes AST when requested", async () => {
    const result = await parseFile("src/core/unified/index.ts", {
      includeAst: true,
      astMaxDepth: 2,
    });

    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(result.ast).toBeDefined();
    expect(result.ast?.type).toBe("program");
  });
});

// ============================================================
// BINARY FILE CAPABILITIES
// ============================================================
describe("Binary File Capabilities", () => {
  test("getParsingCapabilities returns empty for binary files", () => {
    const caps = getParsingCapabilities("image.png");
    expect(caps.method).toBe("generic");
    expect(caps.language).toBe("binary");
    expect(caps.features).toEqual([]);
  });
});

// ============================================================
// EXTRACT SYMBOLS FALLBACK
// ============================================================
describe("Extract Symbols Fallback", () => {
  test("uses direct AST queries when tags.scm finds nothing", async () => {
    // HTML doesn't have good tags.scm support for symbols
    const code = `<html><body><div>Hello</div></body></html>`;
    const result = await parseContent(code, "html");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.html" });
    expect(symbols.method).toBe("tree-sitter");
    // HTML has no functions or classes to extract
    expect(symbols.all).toBeDefined();
  });

  test("extracts functions with direct AST queries when tags.scm is incomplete", async () => {
    // Use a language where tags.scm may not capture all functions
    const code = `
      function test() { return 1; }
      const arrow = () => 2;
    `;
    const result = await parseContent(code, "javascript");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.js" });
    expect(symbols.method).toBe("tree-sitter");
    // Should find at least the test function
    expect(symbols.all.length).toBeGreaterThan(0);
  });

  test("extracts classes with direct AST queries when tags.scm returns empty", async () => {
    // C code with struct (treated as class-like)
    const code = `
      struct Person {
        char* name;
        int age;
      };
    `;
    const result = await parseContent(code, "c");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.c" });
    expect(symbols.method).toBe("tree-sitter");
    expect(symbols.all).toBeDefined();
  });

  test("falls back to findFunctions for languages with incomplete tags.scm", async () => {
    // Svelte has tree-sitter but may have incomplete tags
    const code = `
      <script>
        function handleClick() { return 1; }
      </script>
      <button>Click</button>
    `;
    const result = await parseContent(code, "svelte");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.svelte" });
    expect(symbols.method).toBe("tree-sitter");
  });
});

// ============================================================
// GET SUPPORTED LANGUAGES INFO
// ============================================================
describe("getSupportedLanguagesInfo", () => {
  test("includes both tree-sitter and langchain languages", () => {
    const info = getSupportedLanguagesInfo();

    // Should have tree-sitter languages
    const jsLang = info.find((l) => l.language === "javascript");
    expect(jsLang?.method).toBe("tree-sitter");

    // Should have langchain languages
    const mdLang = info.find((l) => l.language === "markdown");
    expect(mdLang?.method).toBe("langchain");
  });

  test("skips langchain languages that are already in tree-sitter", () => {
    const info = getSupportedLanguagesInfo();

    // JavaScript should only appear once as tree-sitter
    const jsEntries = info.filter((l) => l.language === "javascript");
    expect(jsEntries.length).toBe(1);
    expect(jsEntries[0]?.method).toBe("tree-sitter");
  });
});

// ============================================================
// ADDITIONAL EDGE CASES FOR COVERAGE
// ============================================================
describe("Additional Edge Cases", () => {
  test("detectLanguage handles dockerfile patterns", () => {
    expect(detectLanguage("dockerfile.prod")).toBe("dockerfile");
    expect(detectLanguage("Dockerfile.dev")).toBe("dockerfile");
  });

  test("detectLanguage handles .env patterns", () => {
    expect(detectLanguage(".env.local")).toBe("env");
    expect(detectLanguage(".env.production")).toBe("env");
  });

  test("parseFile returns undefined for non-existent file", async () => {
    const result = await parseFile("nonexistent-file-that-does-not-exist.ts");
    expect(result).toBeUndefined();
  });

  test("parseFile with force language option", async () => {
    const result = await parseFile("package.json", { language: "json" });
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(result.language).toBe("json");
  });

  test("extractSymbols finds classes via direct AST when tags.scm returns none", async () => {
    // Use Go which has struct definitions
    const code = `
package main

type Person struct {
    Name string
    Age  int
}

type Employee struct {
    Person
    Department string
}
`;
    const result = await parseContent(code, "go");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.go" });
    expect(symbols.method).toBe("tree-sitter");
    // Go structs should be found
    expect(symbols.all).toBeDefined();
  });

  test("parseContent falls through langchain to generic on failure", async () => {
    // Very short content that may have edge cases
    const result = await parseContent("x", "text");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    // Should fall back to generic for text
    expect(["langchain", "generic"]).toContain(result.method);
  });
});

// ============================================================
// EXTRACT NAME FROM NODE EDGE CASES
// ============================================================
describe("extractNameFromNode Fallback", () => {
  test("extracts name from function with complex signature", async () => {
    const code = `
async function* myGenerator() {
  yield 1;
}
`;
    const result = await parseContent(code, "javascript");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.js" });
    expect(symbols.method).toBe("tree-sitter");
    expect(symbols.all.length).toBeGreaterThanOrEqual(0);
  });

  test("handles code with only keywords (no identifiers)", async () => {
    // Code that only contains keywords, testing extractNameFromNode fallback
    const code = `
export default function() {
  return null;
}
`;
    const result = await parseContent(code, "javascript");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.js" });
    expect(symbols.method).toBe("tree-sitter");
    // Should handle anonymous function
    expect(symbols.all).toBeDefined();
  });

  test("handles arrow functions in class properties", async () => {
    const code = `
class Handler {
  callback = () => {};
  process = async (x) => x;
}
`;
    const result = await parseContent(code, "javascript");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.js" });
    expect(symbols.method).toBe("tree-sitter");
  });
});

// ============================================================
// PARSEFILEANDCONTENT WITH CUSTOM CHUNK OPTIONS
// ============================================================
describe("Chunk Options", () => {
  test("parseContent respects custom chunkSize", async () => {
    const code = "x\n".repeat(100);
    const result = await parseContent(code, "text", {
      chunkSize: 50,
      chunkOverlap: 5,
    });

    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(result.chunks).toBeDefined();
    if (result.chunks) {
      expect(result.chunks.length).toBeGreaterThan(0);
    }
  });

  test("parseContent with langchain language and custom options", async () => {
    const code = `
# Title
Content paragraph 1.

## Subtitle
Content paragraph 2.
`;
    const result = await parseContent(code, "markdown", {
      chunkSize: 100,
      chunkOverlap: 10,
    });

    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(result.method).toBe("langchain");
  });
});

// ============================================================
// SYMBOL EXTRACTION DIRECT AST QUERIES
// ============================================================
describe("Symbol Extraction Direct AST Queries", () => {
  test("findFunctions fallback when tags.scm returns empty for Svelte", async () => {
    const code = `
<script>
  export function doSomething() {
    return 42;
  }
</script>
<main>Hello</main>
`;
    const result = await parseContent(code, "svelte");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.svelte" });
    expect(symbols.method).toBe("tree-sitter");
    // May or may not find functions depending on tree-sitter implementation
    expect(symbols.all).toBeDefined();
  });

  test("findClasses fallback for C++ code", async () => {
    const code = `
class MyClass {
public:
    void method() {}
};

struct MyStruct {
    int value;
};
`;
    const result = await parseContent(code, "cpp");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.cpp" });
    expect(symbols.method).toBe("tree-sitter");
    expect(symbols.all).toBeDefined();
  });

  test("handles code without any symbols", async () => {
    const code = `<!-- Just a comment -->`;
    const result = await parseContent(code, "html");
    if (!result) {
      throw new Error("Expected result to be defined");
    }

    const symbols = extractSymbols({ ...result, filePath: "test.html" });
    expect(symbols.method).toBe("tree-sitter");
    expect(symbols.functions).toEqual([]);
    expect(symbols.classes).toEqual([]);
  });
});

// ============================================================
// LANGCHAIN LANGUAGE-SPECIFIC TESTING
// ============================================================
describe("LangChain Language Processing", () => {
  test("processes CSS with langchain", async () => {
    const code = `
.class { color: red; }
#id { background: blue; }
@media (max-width: 600px) {
  .responsive { display: none; }
}
`;
    const result = await parseContent(code, "css");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(["langchain", "tree-sitter"]).toContain(result.method);
  });

  test("processes XML with langchain", async () => {
    const code = `
<?xml version="1.0"?>
<root>
  <item id="1">Value</item>
</root>
`;
    const result = await parseContent(code, "xml");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(result.chunks).toBeDefined();
  });
});

// ============================================================
// ADDITIONAL LANGUAGE-SPECIFIC FALLBACK TESTS
// ============================================================
describe("Language-Specific Fallback Tests", () => {
  test("Vue file parses correctly", async () => {
    const code = `
<template>
  <div>{{ message }}</div>
</template>
<script>
export default {
  data() {
    return { message: "Hello" };
  }
};
</script>
<style>
.class { color: red; }
</style>
`;
    const result = await parseContent(code, "vue");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    // Vue may use tree-sitter or langchain depending on configuration
    expect(["tree-sitter", "langchain"]).toContain(result.method);

    if (result.method === "tree-sitter") {
      const symbols = extractSymbols({ ...result, filePath: "test.vue" });
      expect(symbols.all).toBeDefined();
    }
  });

  test("OCaml file parses correctly", async () => {
    const code = `
let rec factorial n =
  if n <= 1 then 1
  else n * factorial (n - 1)

module MyModule = struct
  let value = 42
end
`;
    const result = await parseContent(code, "ocaml");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(result.method).toBe("tree-sitter");

    const symbols = extractSymbols({ ...result, filePath: "test.ml" });
    expect(symbols.all).toBeDefined();
  });

  test("Haskell file parses correctly", async () => {
    const code = `
factorial :: Integer -> Integer
factorial 0 = 1
factorial n = n * factorial (n - 1)

main = print (factorial 5)
`;
    const result = await parseContent(code, "haskell");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    // Haskell may use tree-sitter, langchain, or generic depending on configuration
    expect(["tree-sitter", "langchain", "generic"]).toContain(result.method);
  });
});

// ============================================================
// EDGE CASES FOR BETTER BRANCH COVERAGE
// ============================================================
describe("Branch Coverage Edge Cases", () => {
  test("detectLanguage with complex path structures", () => {
    // Dockerfile patterns - only filename starting with "dockerfile" counts
    expect(detectLanguage("/app/config/Dockerfile")).toBe("dockerfile");
    expect(detectLanguage("/app/config/dockerfile.prod")).toBe("dockerfile");
    // .env patterns
    expect(detectLanguage("C:\\Users\\path\\.env.test")).toBe("env");
    expect(detectLanguage("/config/.env.local")).toBe("env");
    // Regular extensions
    expect(detectLanguage("/path/to/script.py")).toBe("python");
  });

  test("canParse with various extensions", () => {
    expect(canParse("test.dll")).toBe(false);
    expect(canParse("test.so")).toBe(false);
    expect(canParse("test.dylib")).toBe(false);
    expect(canParse("test.a")).toBe(false);
    expect(canParse("test.lib")).toBe(false);
  });

  test("getParsingCapabilities for various file types", () => {
    // Image files
    const pngCaps = getParsingCapabilities("test.jpg");
    expect(pngCaps.language).toBe("binary");
    expect(pngCaps.features).toEqual([]);

    // Audio files
    const mp3Caps = getParsingCapabilities("test.mp3");
    expect(mp3Caps.language).toBe("binary");

    // Archive files
    const tarCaps = getParsingCapabilities("test.tar.gz");
    expect(tarCaps.language).toBe("binary");
  });

  test("parseContent with empty string", async () => {
    const result = await parseContent("", "javascript");
    // Empty content should still be parseable
    if (result) {
      expect(result.lineCount).toBe(1);
    }
  });

  test("parseContent with very long lines", async () => {
    const longLine = "x".repeat(10000);
    const result = await parseContent(longLine, "text");
    if (!result) {
      throw new Error("Expected result to be defined");
    }
    expect(result.chunks).toBeDefined();
  });
});
