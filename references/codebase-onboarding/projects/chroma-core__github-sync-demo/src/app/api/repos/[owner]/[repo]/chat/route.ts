import { openai } from "@ai-sdk/openai";
import {
  convertToModelMessages,
  streamText,
  tool as createTool,
  stepCountIs,
} from "ai";
import type { UIMessage } from "ai";
import {
  db,
  githubRepoState,
  githubRepoDetails,
  githubRepoCommit,
  githubRepoTrees,
  chromaSyncInvocations,
} from "@/db";
import { eq, and } from "drizzle-orm";
import { NextResponse } from "next/server";
import { z } from "zod";
import { validateEnv } from "@/lib/env";
import {
  queryCollection,
  getFileContents,
  grepCollection,
  type GrepResult,
} from "@/services/chroma/client";
import type { GitHubTree } from "@/types/github";
import type { QueryResult } from "@/types/chroma";

validateEnv();

const MAX_SEARCH_RESULTS = 7;
const MAX_TOOL_STEPS = 20;

export const maxDuration = 30;

interface RepoContext {
  collectionName: string;
  description: string | null;
  language: string | null;
  directories: string[];
}

async function getRepoContext(
  owner: string,
  repo: string,
): Promise<RepoContext | null> {
  const repoData = await db
    .select({
      state: githubRepoState,
      details: githubRepoDetails,
      commit: githubRepoCommit,
      tree: githubRepoTrees,
      invocation: chromaSyncInvocations,
    })
    .from(githubRepoState)
    .innerJoin(
      githubRepoDetails,
      eq(githubRepoDetails.name, githubRepoState.repoName),
    )
    .innerJoin(
      chromaSyncInvocations,
      eq(
        chromaSyncInvocations.refIdentifier,
        githubRepoState.latestProcessedCommitSha,
      ),
    )
    .innerJoin(
      githubRepoCommit,
      eq(githubRepoCommit.sha, githubRepoState.latestProcessedCommitSha),
    )
    .leftJoin(
      githubRepoTrees,
      and(
        eq(githubRepoTrees.repoName, githubRepoState.repoName),
        eq(githubRepoTrees.treeSha, githubRepoCommit.treeSha),
      ),
    )
    .where(eq(githubRepoState.repoName, `${owner}/${repo}`))
    .limit(1);

  if (repoData.length === 0) {
    return null;
  }

  const { state, details, tree: treeRow, invocation } = repoData[0];

  if (state.latestCommitSha && !state.latestProcessedCommitSha) {
    return null;
  }

  if (invocation.status !== "completed") {
    return null;
  }

  const rawTree = (treeRow?.tree as GitHubTree["tree"]) ?? [];
  const directories = rawTree
    .filter((entry) => entry.type === "tree")
    .map((entry) => entry.path)
    .sort();

  return {
    collectionName: invocation.targetCollectionName,
    description: details.description || null,
    language: details.language || null,
    directories,
  };
}

function sortByLineNumber(results: QueryResult[]) {
  return results.sort((a, b) => {
    const aStart = a.metadata?.start_line ?? Infinity;
    const bStart = b.metadata?.start_line ?? Infinity;
    return aStart - bStart;
  });
}

function groupResultsByPath(results: QueryResult[]) {
  const grouped = new Map<string, QueryResult[]>();

  for (const result of results) {
    const path = result.metadata?.document_key || "unknown";
    if (!grouped.has(path)) {
      grouped.set(path, []);
    }
    grouped.get(path)!.push(result);
  }

  return Array.from(grouped.entries()).map(([path, chunks]) => {
    const sorted = sortByLineNumber(chunks);
    const content = sorted
      .map((r) => r.document)
      .filter((doc): doc is string => doc !== undefined)
      .join("...");

    return { path, content };
  });
}

function createSearchTool(collectionName: string) {
  return createTool({
    description:
      "Semantic search for code in the repository using natural language.",
    inputSchema: z.object({
      query: z
        .string()
        .describe("Natural language query to search chunks of code"),
    }),
    execute: async ({ query }: { query: string }) => {
      const results = await queryCollection(
        collectionName,
        query,
        MAX_SEARCH_RESULTS,
      );
      return { results: groupResultsByPath(results) };
    },
  });
}

const MAX_CAT_LINES = 1000;

function createCatTool(collectionName: string) {
  return createTool({
    description: "Read the full contents of a file by its path.",
    inputSchema: z.object({
      path: z.string().describe("The file path to read (e.g. 'src/index.ts')"),
    }),
    execute: async ({ path }: { path: string }) => {
      const content = await getFileContents(collectionName, path);
      if (content === null) {
        return { error: `File not found: ${path}` };
      }
      const lines = content.split("\n");
      if (lines.length > MAX_CAT_LINES) {
        const remaining = lines.length - MAX_CAT_LINES;
        const truncated =
          lines.slice(0, MAX_CAT_LINES).join("\n") +
          `\n\n... and ${remaining} more lines`;
        return { path, content: truncated };
      }
      return { path, content };
    },
  });
}

function formatGrepOutput(result: GrepResult): string {
  if (result.totalMatches === 0) {
    return "No matches found.";
  }

  const sections: string[] = [];
  for (const file of result.files) {
    const lines = [file.path];
    for (const match of file.matches) {
      lines.push(`${match.lineNumber}:${match.content}`);
    }
    sections.push(lines.join("\n"));
  }
  return sections.join("\n\n");
}

function createGrepTool(collectionName: string) {
  return createTool({
    description:
      "Search for exact text matches in the repository. Use for finding specific strings, function names, or identifiers.",
    inputSchema: z.object({
      pattern: z
        .string()
        .describe("Text pattern to search for (exact match, not regex)"),
    }),
    execute: async ({ pattern }: { pattern: string }) => {
      const result = await grepCollection(collectionName, pattern);
      return {
        matchCount: result.totalMatches,
        fileCount: result.files.length,
        output: formatGrepOutput(result),
      };
    },
  });
}

function buildSystemPrompt(
  owner: string,
  repo: string,
  context: RepoContext,
): string {
  const lines = [
    `You are a helpful AI assistant that helps users understand the ${owner}/${repo} GitHub repository.`,
  ];

  if (context.description) {
    lines.push(`\nDescription: ${context.description}`);
  }

  if (context.language) {
    lines.push(`Primary language: ${context.language}`);
  }

  if (context.directories.length > 0) {
    lines.push(`\nDirectory structure:`);
    lines.push(...context.directories.map((d) => `  ${d}/`));
  }

  lines.push(`
You have access to tools to search through the repository code and files. Use these tools to provide accurate, context-aware answers about the codebase.

Keep your answers short (aim for less than 3 paragraphs) and focused on the user's question.

The user cannot see the results of the tools you use, so if they want to see something, you must restate it.

Use markdown to format your responses. Use \`\`\`code blocks\`\`\` and inline code \`code\` to make your output more readable.

You can make at most 5 searches each time the user asks a question. Use parallel tool calling to make multiple searches at once. Try to answer the question before hand. If you can't find the answer after 5 searches, succintly describe what you've found.`);

  return lines.join("\n");
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ owner: string; repo: string }> },
) {
  const { owner, repo } = await params;

  try {
    const { messages }: { messages: UIMessage[] } = await req.json();

    const context = await getRepoContext(owner, repo);
    if (!context) {
      return NextResponse.json(
        { error: "Repository not synced or sync incomplete" },
        { status: 400 },
      );
    }

    const result = streamText({
      model: openai("gpt-5"),
      providerOptions: {
        openai: { textVerbosity: "low" },
      },
      system: buildSystemPrompt(owner, repo, context),
      messages: convertToModelMessages(messages),
      tools: {
        search: createSearchTool(context.collectionName),
        cat: createCatTool(context.collectionName),
        grep: createGrepTool(context.collectionName),
      },
      stopWhen: stepCountIs(MAX_TOOL_STEPS),
    });

    return result.toUIMessageStreamResponse({
      sendReasoning: true,
      onError: (error: unknown) => {
        console.error("Chat error:", error);
        const message =
          error instanceof Error ? error.message : "Unknown error";
        return `An error occurred: ${message}`;
      },
    });
  } catch (error) {
    console.error("Chat API Error:", error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 },
    );
  }
}
