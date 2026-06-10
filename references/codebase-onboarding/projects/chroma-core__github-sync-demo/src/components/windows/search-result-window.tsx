"use client";

import React from "react";
import { VimWindow } from "./vim-window";

export interface SearchResultData {
  path: string;
  content: string;
  relevanceScore?: number;
}

interface SearchResultWindowProps {
  result: SearchResultData;
}

export function SearchResultWindow({ result }: SearchResultWindowProps) {
  const header = [
    `# ${result.path}`,
    ...(result.relevanceScore !== undefined
      ? [`# Relevance: ${result.relevanceScore.toFixed(4)}`]
      : []),
    "",
  ].join("\n");

  const bufferContent = header + (result.content || "");

  return <VimWindow initialBuffer={bufferContent} />;
}
