/// <reference types="@cloudflare/workers-types" />
import { DurableObject } from "cloudflare:workers";
import { streamText, tool, stepCountIs, type LanguageModelV1 } from "ai";
import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";
import { createXai } from "@ai-sdk/xai";
import { Bash } from "just-bash";
import { z } from "zod";
//@ts-ignore
import indexHtml from "./index.html";

export interface Env {
  AuthSessions: DurableObjectNamespace<AuthSessions>;
  AI_PROVIDER?: string;
  AI_MODEL?: string;
  AI_API_KEY?: string;
  UITHUB_CLIENT_ID?: string;
  UITHUB_CLIENT_SECRET?: string;
}

const PROVIDER_MODELS: Record<
  string,
  { name: string; keyUrl: string; models: { id: string; label: string }[] }
> = {
  anthropic: {
    name: "Anthropic",
    keyUrl: "https://console.anthropic.com/account/keys",
    models: [
      { id: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
      { id: "claude-opus-4-6", label: "Claude Opus 4.6" },
      { id: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5" }
    ]
  },
  openai: {
    name: "OpenAI",
    keyUrl: "https://platform.openai.com/api-keys",
    models: [
      { id: "gpt-4.1", label: "GPT-4.1" },
      { id: "gpt-4.1-mini", label: "GPT-4.1 Mini" },
      { id: "o3", label: "o3" },
      { id: "o4-mini", label: "o4-mini" }
    ]
  },
  xai: {
    name: "xAI",
    keyUrl: "https://console.x.ai",
    models: [
      { id: "grok-3", label: "Grok 3" },
      { id: "grok-3-mini", label: "Grok 3 Mini" }
    ]
  }
};

function createModel(
  provider: string,
  model: string,
  apiKey: string
): LanguageModelV1 {
  switch (provider) {
    case "openai":
      return createOpenAI({ apiKey })(model);
    case "xai":
      return createXai({ apiKey })(model);
    case "anthropic":
    default:
      return createAnthropic({ apiKey })(model);
  }
}

// ── Durable Object for OAuth sessions ────────────────────────────────────────

export class AuthSessions extends DurableObject<Env> {
  private sql: SqlStorage;

  constructor(state: DurableObjectState, env: Env) {
    super(state, env);
    this.sql = state.storage.sql;
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        access_token TEXT,
        code_verifier TEXT,
        state TEXT,
        client_id TEXT,
        redirect_repos TEXT,
        created_at INTEGER DEFAULT (unixepoch())
      )
    `);
    // Migration: add redirect_repos column to existing tables
    try {
      this.sql.exec(`ALTER TABLE sessions ADD COLUMN redirect_repos TEXT`);
    } catch {
      // Column already exists
    }
  }

  async createSession(
    id: string,
    codeVerifier: string,
    state: string,
    clientId: string,
    redirectRepos?: string
  ): Promise<void> {
    this.sql.exec(
      `INSERT OR REPLACE INTO sessions (id, code_verifier, state, client_id, redirect_repos) VALUES (?, ?, ?, ?, ?)`,
      id,
      codeVerifier,
      state,
      clientId,
      redirectRepos ?? null
    );
  }

  async getSession(id: string): Promise<{
    code_verifier: string;
    state: string;
    access_token: string | null;
    client_id: string | null;
    redirect_repos: string | null;
  } | null> {
    const rows = this.sql
      .exec<{
        code_verifier: string;
        state: string;
        access_token: string | null;
        client_id: string | null;
        redirect_repos: string | null;
      }>(
        `SELECT code_verifier, state, access_token, client_id, redirect_repos FROM sessions WHERE id = ?`,
        id
      )
      .toArray();
    return rows[0] ?? null;
  }

  async setToken(id: string, token: string): Promise<void> {
    this.sql.exec(
      `UPDATE sessions SET access_token = ? WHERE id = ?`,
      token,
      id
    );
  }

  async getToken(id: string): Promise<string | null> {
    const rows = this.sql
      .exec<{
        access_token: string | null;
      }>(`SELECT access_token FROM sessions WHERE id = ?`, id)
      .toArray();
    return rows[0]?.access_token ?? null;
  }

  async deleteSession(id: string): Promise<void> {
    this.sql.exec(`DELETE FROM sessions WHERE id = ?`, id);
  }
}

// ── PKCE helpers ─────────────────────────────────────────────────────────────

function generateRandom(length: number): string {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
  const arr = new Uint8Array(length);
  crypto.getRandomValues(arr);
  return Array.from(arr, (b) => chars[b % chars.length]).join("");
}

async function sha256Base64Url(plain: string): Promise<string> {
  const encoded = new TextEncoder().encode(plain);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  const base64 = btoa(String.fromCharCode(...new Uint8Array(digest)));
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

// ── Cookie helpers ───────────────────────────────────────────────────────────

function getSessionId(request: Request): string | null {
  const cookie = request.headers.get("Cookie") ?? "";
  const match = cookie.match(/session_id=([^;]+)/);
  return match ? match[1] : null;
}

function setSessionCookie(sessionId: string): string {
  return `session_id=${sessionId}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400`;
}

// ── Repo prompt logic (inlined from src/index.ts) ────────────────────────────

interface UithubResponse {
  size: {
    tokens: number;
    totalTokens: number;
    characters: number;
    lines: number;
  };
  tree?: Record<string, unknown>;
  files?: Record<
    string,
    { type: string; content?: string; url?: string; hash: string; size: number }
  >;
}

const AGENT_FILE_GLOBS = [
  "**/AGENTS.md",
  "**/AGENTS.override.md",
  "CLAUDE.md",
  ".claude/settings.json",
  "GEMINI.md",
  ".cursorrules",
  ".cursor/rules/**/*.mdc",
  ".github/copilot-instructions.md",
  ".github/instructions/**/*.instructions.md",
  ".windsurfrules",
  ".windsurf/rules/**/*.md",
  ".clinerules/**",
  ".clinerules",
  "CONVENTIONS.md",
  "CONTRIBUTING.md"
];
const README_GLOBS = ["README.md", "README.rst", "README.txt", "README"];

type AgentFileKind =
  | "agents-md"
  | "claude-md"
  | "gemini-md"
  | "cursorrules"
  | "cursor-rules-dir"
  | "copilot-instructions"
  | "copilot-instructions-dir"
  | "windsurfrules"
  | "clinerules"
  | "conventions-md"
  | "contributing-md"
  | "readme";

interface AgentFile {
  path: string;
  kind: AgentFileKind;
  content: string;
}

function classifyFile(path: string): AgentFileKind | null {
  const lower = path.toLowerCase();
  const base = lower.split("/").pop() ?? "";
  if (base === "agents.md" || base === "agents.override.md") return "agents-md";
  if (base === "claude.md") return "claude-md";
  if (base === "gemini.md") return "gemini-md";
  if (base === ".cursorrules") return "cursorrules";
  if (lower.includes(".cursor/rules/")) return "cursor-rules-dir";
  if (base === "copilot-instructions.md") return "copilot-instructions";
  if (lower.includes(".github/instructions/"))
    return "copilot-instructions-dir";
  if (base === ".windsurfrules") return "windsurfrules";
  if (lower.includes(".windsurf/rules/")) return "windsurfrules";
  if (lower.includes(".clinerules")) return "clinerules";
  if (base === "conventions.md") return "conventions-md";
  if (base === "contributing.md") return "contributing-md";
  if (base.startsWith("readme")) return "readme";
  return null;
}

const KIND_LABELS: Record<AgentFileKind, string> = {
  "agents-md": "AGENTS.md (cross-tool standard)",
  "claude-md": "CLAUDE.md (Claude Code)",
  "gemini-md": "GEMINI.md (Gemini CLI)",
  cursorrules: ".cursorrules (Cursor)",
  "cursor-rules-dir": "Cursor Rules",
  "copilot-instructions": "Copilot Instructions",
  "copilot-instructions-dir": "Copilot Scoped Instructions",
  windsurfrules: "Windsurf Rules",
  clinerules: "Cline Rules",
  "conventions-md": "CONVENTIONS.md",
  "contributing-md": "CONTRIBUTING.md",
  readme: "README"
};

async function fetchFromUithub(
  owner: string,
  repo: string,
  opts: {
    bearerToken?: string;
    include?: string;
    maxTokens?: number;
    omitTree?: boolean;
    omitFiles?: boolean;
  }
): Promise<UithubResponse> {
  const url = new URL(`${owner}/${repo}`, "https://uithub.com");
  if (opts.include) url.searchParams.set("include", opts.include);
  if (opts.maxTokens) url.searchParams.set("maxTokens", String(opts.maxTokens));
  if (opts.omitTree) url.searchParams.set("omitTree", "true");
  if (opts.omitFiles) url.searchParams.set("omitFiles", "true");
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.bearerToken) headers["Authorization"] = `Bearer ${opts.bearerToken}`;
  const res = await fetch(url.toString(), { headers });
  if (!res.ok) throw new Error(`uithub ${res.status}: ${await res.text()}`);
  return res.json() as Promise<UithubResponse>;
}

function renderTree(tree: Record<string, unknown>, prefix = ""): string {
  const entries = Object.entries(tree);
  const lines: string[] = [];
  for (let i = 0; i < entries.length; i++) {
    const [name, value] = entries[i];
    const isLast = i === entries.length - 1;
    const connector = isLast ? "└── " : "├── ";
    const childPrefix = isLast ? "    " : "│   ";
    if (typeof value === "number") {
      lines.push(
        `${prefix}${connector}${name}${value > 0 ? ` (${value} tokens)` : ""}`
      );
    } else if (typeof value === "object" && value !== null) {
      lines.push(`${prefix}${connector}${name}/`);
      lines.push(
        renderTree(value as Record<string, unknown>, prefix + childPrefix)
      );
    }
  }
  return lines.filter(Boolean).join("\n");
}

async function buildRepoPrompt(
  owner: string,
  repo: string,
  bearerToken?: string
) {
  const [treeResponse, filesResponse] = await Promise.all([
    fetchFromUithub(owner, repo, {
      bearerToken,
      omitFiles: true
    }),
    fetchFromUithub(owner, repo, {
      bearerToken,
      include: [...AGENT_FILE_GLOBS, ...README_GLOBS].join(","),
      maxTokens: 50000,
      omitTree: true
    })
  ]);

  const agentFiles: AgentFile[] = [];
  const readmeFiles: AgentFile[] = [];
  if (filesResponse.files) {
    for (const [filePath, fileData] of Object.entries(filesResponse.files)) {
      if (fileData.type !== "content" || !fileData.content) continue;
      const kind = classifyFile(filePath);
      if (!kind) continue;
      const entry: AgentFile = {
        path: filePath,
        kind,
        content: fileData.content
      };
      if (kind === "readme") readmeFiles.push(entry);
      else agentFiles.push(entry);
    }
  }

  const sortByDepth = (a: AgentFile, b: AgentFile) =>
    a.path.split("/").length - b.path.split("/").length;
  agentFiles.sort(sortByDepth);
  readmeFiles.sort(sortByDepth);

  const sections: string[] = [];
  sections.push(
    `# Repository: ${owner}/${repo}\nTotal size: ~${treeResponse.size.totalTokens.toLocaleString()} tokens`
  );
  if (agentFiles.length > 0) {
    sections.push("---\n## Agent Instructions\n");
    for (const file of agentFiles) {
      sections.push(
        `### ${KIND_LABELS[file.kind] ?? file.kind}\n<!-- source: ${file.path} -->\n\n${file.content.trim()}`
      );
    }
  }
  if (readmeFiles.length > 0) {
    sections.push("---\n## README Files\n");
    for (const file of readmeFiles) {
      const header =
        readmeFiles.length === 1 ? "### README" : `### ${file.path}`;
      sections.push(
        `${header}\n<!-- source: ${file.path} -->\n\n${file.content.trim()}`
      );
    }
  }
  if (treeResponse.tree) {
    sections.push(
      "---\n## File Tree\n```\n" + renderTree(treeResponse.tree) + "\n```"
    );
  }
  return {
    prompt: sections.join("\n\n"),
    tree: treeResponse.tree ?? null,
    size: treeResponse.size
  };
}

async function buildFullContextPrompt(
  owner: string,
  repo: string,
  bearerToken?: string
) {
  const response = await fetchFromUithub(owner, repo, {
    bearerToken,
    maxTokens: 1000000
  });

  if (response.size.totalTokens > 1000000) {
    throw new Error(
      `Repository ${owner}/${repo} is too large for full context (~${response.size.totalTokens.toLocaleString()} tokens, max 1,000,000). Use "Tree & READMEs" strategy instead.`
    );
  }

  const sections: string[] = [];
  sections.push(
    `# Repository: ${owner}/${repo}\nTotal size: ~${response.size.totalTokens.toLocaleString()} tokens`
  );

  if (response.tree) {
    sections.push(
      "---\n## File Tree\n```\n" + renderTree(response.tree) + "\n```"
    );
  }

  if (response.files) {
    sections.push("---\n## Files\n");
    for (const [filePath, fileData] of Object.entries(response.files)) {
      if (fileData.type !== "content" || !fileData.content) continue;
      const ext = filePath.split(".").pop() || "";
      sections.push(
        `### ${filePath}\n\`\`\`${ext}\n${fileData.content}\n\`\`\``
      );
    }
  }

  return {
    prompt: sections.join("\n\n"),
    tree: response.tree ?? null,
    size: response.size
  };
}

// ── Fetch all repo files for bash sandbox ────────────────────────────────────

async function fetchRepoFiles(
  owner: string,
  repo: string,
  bearerToken?: string
): Promise<Record<string, string>> {
  const response = await fetchFromUithub(owner, repo, {
    bearerToken,
    maxTokens: 100000000
  });
  const files: Record<string, string> = {};
  if (response.files) {
    for (const [filePath, fileData] of Object.entries(response.files)) {
      if (fileData.type === "content" && fileData.content) {
        files[`/workspace/${filePath}`] = fileData.content;
      }
    }
  }
  return files;
}

// ── Chat handler using AI SDK + bash-tool ────────────────────────────────────

async function handleChat(
  request: Request,
  env: Env,
  sessionStub: DurableObjectStub<AuthSessions>,
  sessionId: string
): Promise<Response> {
  const body = (await request.json()) as {
    messages: Array<{ role: "user" | "assistant"; content: string }>;
    repos: string[];
    strategy?: string;
    // legacy
    owner?: string;
    repo?: string;
    systemPrompt: string;
    provider?: string;
    model?: string;
    apiKey?: string;
  };
  const { messages, systemPrompt } = body;
  const strategy = body.strategy || "tree-readmes";

  const aiProvider = body.provider || env.AI_PROVIDER || "anthropic";
  const aiModel = body.model || env.AI_MODEL || "claude-sonnet-4-6";
  const aiApiKey = body.apiKey || env.AI_API_KEY;
  if (!aiApiKey) {
    return new Response("No API key configured. Open Settings to add one.", {
      status: 400
    });
  }
  const repos: string[] = body.repos?.length
    ? body.repos
    : body.owner && body.repo
      ? [`${body.owner}/${body.repo}`]
      : [];
  if (!messages || repos.length === 0 || !systemPrompt) {
    return new Response("Missing required fields", { status: 400 });
  }

  const model = createModel(aiProvider, aiModel, aiApiKey);

  if (strategy === "full-context") {
    // No tools needed — all file contents are in the system prompt
    const result = streamText({
      model,
      system: systemPrompt,
      messages
    });
    return result.toUIMessageStreamResponse();
  }

  const bearerToken = (await sessionStub.getToken(sessionId)) ?? undefined;

  // Fetch repo files from all repos and create a just-bash virtual environment
  const allFiles: Record<string, string> = {};
  await Promise.all(
    repos.map(async (r) => {
      const [owner, repo] = r.split("/");
      const files = await fetchRepoFiles(owner, repo, bearerToken);
      // Namespace files under /workspace/{owner}/{repo}/
      for (const [filePath, content] of Object.entries(files)) {
        // filePath is /workspace/path — remap to /workspace/{owner}/{repo}/path
        const relative = filePath.replace(/^\/workspace\//, "");
        allFiles[`/workspace/${owner}/${repo}/${relative}`] = content;
      }
    })
  );
  const bash = new Bash({ files: allFiles, cwd: "/workspace" });

  const result = streamText({
    model,
    system: systemPrompt,
    messages,
    tools: {
      bash: tool({
        description:
          "Execute a bash command in a virtual environment containing the repository files at /workspace/{owner}/{repo}/. " +
          "Supports standard Unix commands: cat, grep, find, sed, awk, ls, head, tail, wc, sort, uniq, diff, jq, etc.",
        inputSchema: z.object({
          command: z.string().describe("The bash command to execute")
        }),
        execute: async ({ command }: { command: string }) => {
          const result = await bash.exec(`cd /workspace && ${command}`);
          const truncate = (s: string) =>
            s.length > 30000 ? s.slice(0, 30000) + "\n...[truncated]" : s;
          return `stdout: ${truncate(result.stdout)}\nstderr: ${truncate(result.stderr)}\nexitCode: ${result.exitCode}`;
        }
      }),
      readFile: tool({
        description:
          "Read the full contents of a file from the virtual environment. Files are under /workspace/{owner}/{repo}/.",
        inputSchema: z.object({
          path: z
            .string()
            .describe(
              "Absolute path to the file, e.g. /workspace/owner/repo/src/index.ts"
            )
        }),
        execute: async ({ path }: { path: string }) => {
          try {
            return await bash.readFile(path);
          } catch (e: any) {
            return `Error: ${e.message || "Failed to read file"}`;
          }
        }
      })
    },
    stopWhen: stepCountIs(30)
  });

  return result.toUIMessageStreamResponse();
}

// ── Dynamic client registration helper ───────────────────────────────────────

async function getOrRegisterClient(env: Env, origin: string): Promise<string> {
  if (env.UITHUB_CLIENT_ID) return env.UITHUB_CLIENT_ID;
  const res = await fetch("https://uithub.com/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_name: "Chat for GitHub",
      redirect_uris: [`${origin}/auth/callback`],
      token_endpoint_auth_method: "none"
    })
  });
  if (!res.ok)
    throw new Error(`Client registration failed: ${await res.text()}`);
  return ((await res.json()) as { client_id: string }).client_id;
}

// ── Main handler ─────────────────────────────────────────────────────────────

export default {
  async fetch(
    request: Request,
    env: Env,
    _ctx: ExecutionContext
  ): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // ── Redirect /github.com/:owner/:repo → ?repo=owner/repo ────────
    const ghMatch = path.match(/^\/github\.com\/([^/]+\/[^/]+)\/?$/);
    if (ghMatch) {
      const target = new URL("/", url.origin);
      target.searchParams.set("repo", ghMatch[1]);
      return Response.redirect(target.toString(), 302);
    }

    // ── API: available providers/models ───────────────────────────────
    if (path === "/api/config") {
      return Response.json({ providers: PROVIDER_MODELS });
    }

    const sessionId = getSessionId(request) ?? generateRandom(32);
    const doId = env.AuthSessions.idFromName("global");
    const sessionStub = env.AuthSessions.get(doId);

    // ── OAuth: start login ───────────────────────────────────────────────
    if (path === "/auth/login") {
      const codeVerifier = generateRandom(64);
      const state = generateRandom(32);
      const codeChallenge = await sha256Base64Url(codeVerifier);
      const clientId = await getOrRegisterClient(env, url.origin);

      const repos = url.searchParams
        .getAll("repo")
        .filter((r) => r.includes("/"));
      const redirectRepos =
        repos.length > 0 ? JSON.stringify(repos) : undefined;

      await sessionStub.createSession(
        sessionId,
        codeVerifier,
        state,
        clientId,
        redirectRepos
      );

      const authUrl = new URL("https://uithub.com/authorize");
      authUrl.searchParams.set("client_id", clientId);
      authUrl.searchParams.set("redirect_uri", `${url.origin}/auth/callback`);
      authUrl.searchParams.set("response_type", "code");
      authUrl.searchParams.set("scope", "read repo");
      authUrl.searchParams.set("state", state);
      authUrl.searchParams.set("code_challenge", codeChallenge);
      authUrl.searchParams.set("code_challenge_method", "S256");

      return new Response(null, {
        status: 302,
        headers: {
          Location: authUrl.toString(),
          "Set-Cookie": setSessionCookie(sessionId)
        }
      });
    }

    // ── OAuth: callback ──────────────────────────────────────────────────
    if (path === "/auth/callback") {
      const code = url.searchParams.get("code");
      const state = url.searchParams.get("state");
      if (!code || !state)
        return new Response("Missing code or state", { status: 400 });

      const currentSessionId = getSessionId(request);
      if (!currentSessionId)
        return new Response("No session cookie", { status: 400 });

      const session = await sessionStub.getSession(currentSessionId);
      if (!session || session.state !== state)
        return new Response("Invalid state", { status: 400 });

      const clientId =
        session.client_id || (await getOrRegisterClient(env, url.origin));

      const tokenRes = await fetch("https://uithub.com/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          grant_type: "authorization_code",
          code,
          redirect_uri: `${url.origin}/auth/callback`,
          client_id: clientId,
          code_verifier: session.code_verifier
        })
      });
      if (!tokenRes.ok)
        return new Response(`Token exchange failed: ${await tokenRes.text()}`, {
          status: 500
        });

      const tokenData = (await tokenRes.json()) as { access_token: string };
      await sessionStub.setToken(currentSessionId, tokenData.access_token);

      const redirectUrl = new URL("/", url.origin);
      if (session.redirect_repos) {
        try {
          const repos = JSON.parse(session.redirect_repos) as string[];
          for (const repo of repos) {
            redirectUrl.searchParams.append("repo", repo);
          }
        } catch {}
      }

      return new Response(null, {
        status: 302,
        headers: { Location: redirectUrl.toString() }
      });
    }

    // ── Auth status ──────────────────────────────────────────────────────
    if (path === "/auth/status") {
      const sid = getSessionId(request);
      if (!sid) return Response.json({ authenticated: false });
      const token = await sessionStub.getToken(sid);
      return Response.json({ authenticated: !!token });
    }

    // ── Logout ───────────────────────────────────────────────────────────
    if (path === "/auth/logout") {
      const sid = getSessionId(request);
      if (sid) await sessionStub.deleteSession(sid);
      return new Response(null, {
        status: 302,
        headers: {
          Location: "/",
          "Set-Cookie": "session_id=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
        }
      });
    }

    // ── Redirect /:owner/:repo → /?repo=owner/repo ─────────────────────
    const pathParts = path.split("/").filter(Boolean);
    if (
      pathParts.length >= 2 &&
      !["auth", "api"].includes(pathParts[0]) &&
      request.method === "GET"
    ) {
      const repoSlug = `${pathParts[0]}/${pathParts[1]}`;
      const redirectUrl = new URL("/", url.origin);
      redirectUrl.searchParams.set("repo", repoSlug);
      return new Response(null, {
        status: 302,
        headers: { Location: redirectUrl.toString() }
      });
    }

    // ── API: build system prompt (supports multiple repos) ───────────────
    if (path === "/api/prompt" && request.method === "POST") {
      const body = (await request.json()) as {
        repos: string[];
        strategy?: string;
        // legacy single-repo support
        owner?: string;
        repo?: string;
      };
      const repos: string[] = body.repos?.length
        ? body.repos
        : body.owner && body.repo
          ? [`${body.owner}/${body.repo}`]
          : [];
      if (repos.length === 0)
        return new Response("Missing repos", { status: 400 });

      const strategy = body.strategy || "tree-readmes";
      const sid = getSessionId(request);
      const bearerToken = sid ? await sessionStub.getToken(sid) : null;
      try {
        const builder =
          strategy === "full-context" ? buildFullContextPrompt : buildRepoPrompt;
        const results = await Promise.all(
          repos.map((r) => {
            const [owner, repo] = r.split("/");
            return builder(owner, repo, bearerToken ?? undefined);
          })
        );
        const combinedPrompt = results.map((r) => r.prompt).join("\n\n---\n\n");
        const combinedSize = {
          tokens: results.reduce((s, r) => s + r.size.tokens, 0),
          totalTokens: results.reduce((s, r) => s + r.size.totalTokens, 0),
          characters: results.reduce((s, r) => s + r.size.characters, 0),
          lines: results.reduce((s, r) => s + r.size.lines, 0)
        };
        return Response.json({ prompt: combinedPrompt, size: combinedSize });
      } catch (e: any) {
        return Response.json({ error: e.message }, { status: 502 });
      }
    }

    // ── API: chat stream ─────────────────────────────────────────────────
    if (path === "/api/chat" && request.method === "POST") {
      const sid = getSessionId(request) ?? sessionId;
      return handleChat(request, env, sessionStub, sid);
    }

    return new Response(indexHtml, {
      headers: { "Content-Type": "text/html;charset=utf8" }
    });
  }
} satisfies ExportedHandler<Env>;
