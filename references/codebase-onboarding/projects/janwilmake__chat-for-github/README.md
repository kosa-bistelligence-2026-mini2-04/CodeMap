# Chat for GitHub

Chat with any GitHub repository using AI. Hosted at [chat.forgithub.com](https://chat.forgithub.com).

Load one or more repos, and start a conversation. The AI can read files, run bash commands, and explore the codebase to answer your questions.

## Features

- **Bring your own key** — configure your preferred AI provider and model in the Settings modal
- **Multi-provider** — supports Anthropic, OpenAI, and xAI (Grok)
- **Multi-repo support** — load multiple repositories into a single conversation
- **Full codebase access** — all repo files are fetched and mounted in a virtual filesystem at `/workspace/{owner}/{repo}/`
- **Tool use** — the AI can run bash commands (`grep`, `find`, `cat`, `jq`, etc.) and read files to explore the code
- **Agent instructions** — automatically discovers and prioritizes `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.github/copilot-instructions.md`, and other AI coding standards
- **Private repos** — OAuth login via [uithub](https://uithub.com) to access private repositories
- **Conversation history** — saved locally in your browser
- **Dark mode** — follows system preference

## Supported Models

| Provider | Model | ID |
|---|---|---|
| **Anthropic** | Claude Sonnet 4.6 | `claude-sonnet-4-6` |
| | Claude Opus 4.6 | `claude-opus-4-6` |
| | Claude Haiku 4.5 | `claude-haiku-4-5-20251001` |
| **OpenAI** | GPT-4.1 | `gpt-4.1` |
| | GPT-4.1 Mini | `gpt-4.1-mini` |
| | o3 | `o3` |
| | o4-mini | `o4-mini` |
| **xAI** | Grok 3 | `grok-3` |
| | Grok 3 Mini | `grok-3-mini` |

Get an API key: [Anthropic](https://console.anthropic.com/account/keys) | [OpenAI](https://platform.openai.com/api-keys) | [xAI](https://console.x.ai)

## How It Works

```
Browser → Cloudflare Worker → uithub (repo context) + AI provider (user-configured)
```

1. You pick a provider, model, and paste your API key in **Settings** (stored in your browser)
2. You enter one or more GitHub repos (e.g. `vercel/next.js`)
3. The worker fetches the repo tree and agent instruction files from [uithub.com](https://uithub.com)
4. A system prompt is built with agent instructions, READMEs, and the file tree
5. When you send a message, the worker fetches all repo files, mounts them in a virtual bash environment, and streams the AI response back — including any tool calls

## Tech Stack

- **Runtime:** Cloudflare Workers
- **AI:** [Vercel AI SDK](https://sdk.vercel.ai) with `@ai-sdk/anthropic`, `@ai-sdk/openai`, `@ai-sdk/xai`
- **Repo context:** [uithub.com](https://uithub.com)
- **Virtual shell:** [just-bash](https://www.npmjs.com/package/just-bash)
- **Sessions:** Cloudflare Durable Objects (SQLite-backed)
- **Frontend:** Single HTML file, vanilla JS, no framework

## Development

```bash
npm install
npm run dev     # start local dev server
npm run deploy  # deploy to Cloudflare
```

### Configuration

Users configure their AI provider, model, and API key through the in-app **Settings** modal. Keys are stored in the browser's localStorage and sent per-request.

For self-hosted deployments, you can optionally set server-side fallback values via `wrangler secret put`:

| Variable | Description |
|---|---|
| `AI_PROVIDER` | `anthropic`, `openai`, or `xai` |
| `AI_MODEL` | Model ID from the table above |
| `AI_API_KEY` | API key for the selected provider |
| `UITHUB_CLIENT_ID` | uithub OAuth client ID (auto-registered if omitted) |
| `UITHUB_CLIENT_SECRET` | uithub OAuth client secret |

## License

MIT
