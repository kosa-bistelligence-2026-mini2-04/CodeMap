"use client";

import React from "react";
import { VimWindow } from "./vim-window";

interface ToolCallWindowProps {
  toolName: string;
  input: Record<string, unknown>;
  output?: unknown;
}

interface ToolConfig {
  title: string;
  description: string;
  parameters: Array<{
    key: string;
    label?: string;
    formatter?: (value: unknown) => string;
    condition?: (input: Record<string, unknown>) => boolean;
  }>;
}

const TOOL_CONFIGS: Record<string, ToolConfig> = {
  package_search_grep: {
    title: "# package_search_grep",
    description:
      "Searches for exact pattern matches within package code using regular expressions.",
    parameters: [
      { key: "registry_name" },
      { key: "package_name" },
      {
        key: "pattern",
        formatter: (value) => `/${value}/g`,
      },
      { key: "head_limit", condition: (input) => !!input.head_limit },
    ],
  },
  package_search_hybrid: {
    title: "# package_search_hybrid",
    description:
      "Combines semantic search with pattern matching for more intelligent code discovery",
    parameters: [
      { key: "registry_name" },
      { key: "package_name" },
      {
        key: "semantic_queries",
        condition: (input) => !!input.semantic_queries,
        formatter: (value) => {
          if (Array.isArray(value)) {
            return value.map((q: string) => `  - ${q}`).join("\n");
          }
          return String(value);
        },
      },
      {
        key: "pattern",
        condition: (input) => !!input.pattern,
        formatter: (value) => `/${value}/g`,
      },
      { key: "head_limit", condition: (input) => !!input.head_limit },
    ],
  },
  package_search_read_file: {
    title: "# package_search_read_file",
    description:
      "Reads specific lines from a file in a package using its SHA256 hash",
    parameters: [
      { key: "registry_name" },
      { key: "package_name" },
      { key: "filename_sha256", label: "File SHA256" },
      { key: "start_line", condition: (input) => !!input.start_line },
      { key: "end_line", condition: (input) => !!input.end_line },
    ],
  },
};

function formatToolCall(
  toolName: string,
  input: Record<string, unknown>,
): string {
  const config = TOOL_CONFIGS[toolName];

  if (config) {
    const lines: string[] = [config.title, config.description, ""];

    for (const { key, label, formatter, condition } of config.parameters) {
      if (condition && !condition(input)) continue;

      const value = input[key];
      if (value === undefined) continue;

      const displayLabel = label || key;
      const displayValue = formatter ? formatter(value) : String(value);

      if (displayValue.includes("\n")) {
        lines.push(`${displayLabel}:`);
        lines.push(displayValue);
      } else {
        lines.push(`${displayLabel}: ${displayValue}`);
      }
    }

    return lines.join("\n");
  }

  const lines: string[] = [
    `# ${toolName}`,
    "# Tool call details and parameters",
    "",
  ];

  lines.push("input:");
  lines.push(JSON.stringify(input, null, 2));

  return lines.join("\n");
}

export function ToolCallWindow({ toolName, input }: ToolCallWindowProps) {
  const bufferContent = formatToolCall(toolName, input);
  return <VimWindow initialBuffer={bufferContent} />;
}
