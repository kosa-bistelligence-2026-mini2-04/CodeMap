# GitHub Repository Chat

Chat with any GitHub repository using AI.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fchroma-core%2Fgithub-sync-demo&env=CHROMA_API_KEY,CHROMA_TENANT,CHROMA_DATABASE,OPENAI_API_KEY,DATABASE_URL,GITHUB_TOKEN&project-name=chat-with-github&repository-name=chat-with-github&demo-title=Chat%20With%20Github&demo-description=Chat%20with%20any%20Github%20repository%20using%20AI&demo-url=github-sync-demo.vercel.app)

![preview](doc/1203.gif)

## How It Works

When a user searches for a repo, it will automatically index the repo in Chroma using the Chroma Sync API.

The Chroma Sync API will automatically chunk, embed, and insert the repo files into a Chroma collection,
and can be queried like any other Chroma collection.

The Chroma Sync API is aware of the Git tree, so it only needs to re-index that have changed since the last sync.

## Quick Start

Sign up for [Chroma Cloud](https://trychroma.com), make a database and get your
Chroma credentials.

Create a `.env.local` file with the following variables:

```bash
CHROMA_API_KEY=your_chroma_api_key
CHROMA_TENANT=your_chroma_tenant
CHROMA_DATABASE=your_chroma_database

GITHUB_APP_ID=your_github_app_id
GITHUB_TOKEN=your_github_personal_access_token

# Postgres Database
DATABASE_URL=postgresql://user:password@host:port/database

# OpenTelemetry Configuration (Optional)
# OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces

OPENAI_API_KEY=your_openai_api_key
```

```bash
pnpm install

# Push schema to database
pnpm run db:generate
pnpm run db:push

pnpm dev
```

Your app template should now be running on [localhost:3000](http://localhost:3000).

## Model Providers

This template ships with OpenAI gpt-5.1 as the default. However, with the AI SDK, you can switch LLM providers to
Anthropic, Cohere, and many more with just a few lines of code.
