/**
 * LangChain text splitter fallback for languages without Tree-sitter support
 */
import {
  RecursiveCharacterTextSplitter,
  type SupportedTextSplitterLanguage,
} from "@langchain/textsplitters";

import { loadJsonConfig, registerCache } from "@core/utils";

interface LangChainConfig {
  mapping: Record<string, string>;
  supported: string[];
  generic: string[];
}

interface FullConfig {
  langchain: LangChainConfig;
}

let langchainConfig: LangChainConfig | null = null;

function loadConfig(): LangChainConfig {
  if (langchainConfig) {
    return langchainConfig;
  }

  const defaultConfig: FullConfig = {
    langchain: { mapping: {}, supported: [], generic: [] },
  };
  const fullConfig = loadJsonConfig<FullConfig>(
    "languages.json",
    defaultConfig,
  );
  langchainConfig = fullConfig.langchain;
  return langchainConfig;
}

export interface TextChunk {
  content: string;
  startLine: number;
  endLine: number;
  index: number;
}

export interface TextSplitResult {
  chunks: TextChunk[];
  count: number;
  language: string;
  method: "text-splitter";
}

export interface TextSplitOptions {
  chunkSize?: number;
  chunkOverlap?: number;
}

export function isTextSplitterLanguage(language: string): boolean {
  const config = loadConfig();
  return (
    language in config.mapping ||
    config.supported.includes(language) ||
    config.generic.includes(language)
  );
}

export function getTextSplitterLanguage(
  language: string,
): SupportedTextSplitterLanguage | undefined {
  const config = loadConfig();

  if (language in config.mapping) {
    return config.mapping[language] as SupportedTextSplitterLanguage;
  }
  if (config.supported.includes(language)) {
    return language as SupportedTextSplitterLanguage;
  }
  return undefined;
}

function calculateLineNumbers(
  fullContent: string,
  chunkContent: string,
  startSearchIndex: number,
): { startLine: number; endLine: number; foundIndex: number } {
  const chunkIndex = fullContent.indexOf(chunkContent, startSearchIndex);
  const actualIndex = chunkIndex >= 0 ? chunkIndex : startSearchIndex;
  const beforeChunk = fullContent.slice(0, actualIndex);
  const startLine = (beforeChunk.match(/\n/g) ?? []).length + 1;
  const chunkLines = (chunkContent.match(/\n/g) ?? []).length;
  return {
    startLine,
    endLine: startLine + chunkLines,
    foundIndex: actualIndex + chunkContent.length,
  };
}

export async function splitCode(
  content: string,
  language: string,
  options: TextSplitOptions = {},
): Promise<TextSplitResult> {
  const { chunkSize = 1000, chunkOverlap = 200 } = options;
  const splitterLanguage = getTextSplitterLanguage(language);

  const splitter = splitterLanguage
    ? RecursiveCharacterTextSplitter.fromLanguage(splitterLanguage, {
        chunkSize,
        chunkOverlap,
      })
    : new RecursiveCharacterTextSplitter({ chunkSize, chunkOverlap });

  const docs = await splitter.createDocuments([content]);
  const chunks: TextChunk[] = [];
  let searchIndex = 0;

  for (const [i, doc] of docs.entries()) {
    const { startLine, endLine, foundIndex } = calculateLineNumbers(
      content,
      doc.pageContent,
      searchIndex,
    );
    searchIndex = foundIndex;
    chunks.push({ content: doc.pageContent, startLine, endLine, index: i });
  }

  return { chunks, count: chunks.length, language, method: "text-splitter" };
}

export function getSeparators(language: string): string[] {
  const splitterLanguage = getTextSplitterLanguage(language);
  return splitterLanguage
    ? RecursiveCharacterTextSplitter.getSeparatorsForLanguage(splitterLanguage)
    : [];
}

export function clearConfigCache(): void {
  langchainConfig = null;
}

// Register cache for centralized clearing
registerCache("fallback:config", clearConfigCache);
