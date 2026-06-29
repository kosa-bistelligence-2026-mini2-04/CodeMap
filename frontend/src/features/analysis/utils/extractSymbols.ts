/**
 * 코드 내비게이션(Symbols) — 파일 내용에서 핵심 심볼을 추출하는 경량 휴리스틱 파서.
 *
 * Monaco의 Document Symbol Provider는 일부 언어(TS/JS)에만 풍부하게 제공되므로,
 * 언어에 상관없이 일관된 Symbols 패널을 제공하기 위해 정규식 기반으로 추출한다.
 * (Issue #206)
 */

export type SymbolKind =
  | "class"
  | "interface"
  | "enum"
  | "type"
  | "struct"
  | "function"
  | "method"
  | "const";

export type SymbolCategory = "class" | "function" | "const";

export interface CodeSymbol {
  name: string;
  kind: SymbolKind;
  line: number; // 1-based
}

const CATEGORY_BY_KIND: Record<SymbolKind, SymbolCategory> = {
  class: "class",
  interface: "class",
  enum: "class",
  struct: "class",
  type: "const",
  function: "function",
  method: "function",
  const: "const",
};

export function symbolCategory(kind: SymbolKind): SymbolCategory {
  return CATEGORY_BY_KIND[kind];
}

interface Rule {
  re: RegExp;
  kind: SymbolKind;
}

const PY_RULES: Rule[] = [
  { re: /^\s*class\s+([A-Za-z_]\w*)/, kind: "class" },
  { re: /^(\s*)(?:async\s+)?def\s+([A-Za-z_]\w*)/, kind: "function" },
];

const JS_RULES: Rule[] = [
  { re: /^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)/, kind: "class" },
  { re: /^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)/, kind: "interface" },
  { re: /^\s*(?:export\s+)?(?:declare\s+)?(?:const\s+)?enum\s+([A-Za-z_$][\w$]*)/, kind: "enum" },
  { re: /^\s*(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*[=<]/, kind: "type" },
  { re: /^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s+([A-Za-z_$][\w$]*)/, kind: "function" },
  { re: /^\s*(?:export\s+)?(?:const|let)\s+([A-Za-z_$][\w$]*)\s*[:=]/, kind: "const" },
];

const GO_RULES: Rule[] = [
  { re: /^\s*type\s+([A-Za-z_]\w*)\s+struct\b/, kind: "struct" },
  { re: /^\s*type\s+([A-Za-z_]\w*)\s+interface\b/, kind: "interface" },
  { re: /^\s*type\s+([A-Za-z_]\w*)\b/, kind: "type" },
  { re: /^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)/, kind: "function" },
  { re: /^\s*const\s+([A-Za-z_]\w*)/, kind: "const" },
];

const GENERIC_RULES: Rule[] = [
  { re: /^\s*(?:public|private|protected|internal|static|final|abstract|\s)*class\s+([A-Za-z_]\w*)/, kind: "class" },
  { re: /^\s*(?:public|private|protected|internal|\s)*interface\s+([A-Za-z_]\w*)/, kind: "interface" },
  { re: /^\s*(?:export\s+)?(?:async\s+)?(?:function|func|def|fn)\s+([A-Za-z_]\w*)/, kind: "function" },
  { re: /^\s*const\s+([A-Za-z_]\w*)/, kind: "const" },
];

function rulesFor(language: string | null): Rule[] {
  const lang = (language ?? "").toLowerCase();
  if (lang === "python") return PY_RULES;
  if (["typescript", "tsx", "javascript", "jsx"].includes(lang)) return JS_RULES;
  if (lang === "go") return GO_RULES;
  return GENERIC_RULES;
}

/**
 * 파일 내용에서 심볼 목록을 추출한다. (1-based line)
 * 같은 라인에서는 가장 먼저 매칭된 규칙만 사용한다.
 */
export function extractSymbols(content: string, language: string | null): CodeSymbol[] {
  if (!content) return [];
  const rules = rulesFor(language);
  const isPython = (language ?? "").toLowerCase() === "python";
  const lines = content.split("\n");
  const symbols: CodeSymbol[] = [];

  lines.forEach((rawLine, idx) => {
    for (const rule of rules) {
      const m = rawLine.match(rule.re);
      if (!m) continue;
      // 파이썬 def 규칙은 (들여쓰기, 이름) 두 그룹을 사용한다.
      let name: string;
      let kind: SymbolKind = rule.kind;
      if (isPython && rule.kind === "function") {
        const indent = m[1] ?? "";
        name = m[2];
        if (indent.length > 0) kind = "method";
      } else {
        name = m[1];
      }
      if (!name) continue;
      symbols.push({ name, kind, line: idx + 1 });
      break;
    }
  });

  return symbols;
}
