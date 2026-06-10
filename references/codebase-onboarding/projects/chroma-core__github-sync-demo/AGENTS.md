# AGENTS.md

## Project Summary

This is a Next.js application that enables AI-powered chat with GitHub repositories using semantic code search. Users enter a repository URL, and the app:

1. Fetches repository metadata and commit information from the GitHub API
2. Syncs the repository code to Chroma using the Chroma Sync API (indexes code with Qwen/Qwen3-Embedding-0.6B)
3. Stores repository metadata, commits, and sync status in PostgreSQL
4. Provides a chat interface powered by OpenAI that queries the Chroma vector database for relevant code

The database tracks repositories, commits, Chroma sync sources, and invocation status. Repositories are automatically re-synced if the last invocation failed or if both the last commit fetch and last invocation are older than 24 hours.

## API

The api endpoints are designed not to have race conditions using row-level locking.

### /api/repos/[owner]/[repo]/chat

LLM chat. It provides the latest successful invocation collection as a resource for its tools.

### GET /api/repos/[owner]/[repo]/status

1. Gets the stored repo, latest commit, corresponding repo tree, and invocation if it exists.
2. If the invocation exists but is out of date (>2s old) and is not terminal, it will get the latest value from the chroma sync API.
   In order to prevent multiple simultaneus requests from making my API make multiple extraneous requests to the chroma sync API for the same
   resource, this route uses a row-level lock to make sure that only one concurrent request is able to make the API call to the external chroma sync API
   and update the value in the row.
3. Return the results. If the current value is out of date and the row has a lock (meaning something is currently updating the value), then immediately
   return the out of date value currently stored in the DB.

## Chroma Sync API

Base URL: `https://sync.trychroma.com/api/v1`

### POST `/sources`

Create a source for a GitHub repository.

**Request:**

```json
{
  "github": {
    "include_globs": ["**/*"],
    "repository": "owner/repo"
  },
  "database_name": "string",
  "embedding": {
    "dense": {
      "model": "Qwen/Qwen3-Embedding-0.6B",
      "task": null
    },
    "sparse": null
  },
  "embedding_model": null
}
```

**Response:**

```json
{
  "source_id": "uuid"
}
```

### POST `/sources/{source_id}/invocations`

Create an invocation to index code for a specific commit SHA.

**Request:**

```json
{
  "ref_identifier": {
    "sha": "commit-sha"
    },
  "target_collection_name": "uuid"
}
```

**Response:**

```json
{
  "invocation_id": "uuid"
}
```

### GET `/invocations/{invocation_id}`

Get invocation status.

**Response:**

```json
{
  "id": "uuid",
  "status": "pending" | "processing" | "completed" | "failed" | { "complete": { "duration_ms": number, "finished_at": "string" } } | { "failed": { "error": "string" } },
  "created_at": "ISO8601",
  "metadata": {
    "collection_name": "string",
    "database_name": "string"
  }
}
```

## GitHub API

### GET `/repos/{owner}/{repo}`

**Fields used:**

- `full_name`, `description`, `default_branch`, `html_url`, `language`
- `stargazers_count`, `forks_count`, `watchers_count`, `open_issues_count`, `subscribers_count`
- `fork`, `private`, `license.name`

### GET `/repos/{owner}/{repo}/branches/{branch}`

**Fields used:**

- `commit.sha`
- `commit.commit.tree.sha`
- `commit.commit.message`
- `commit.commit.author.name`
- `commit.commit.author.date`
- `commit.html_url`
