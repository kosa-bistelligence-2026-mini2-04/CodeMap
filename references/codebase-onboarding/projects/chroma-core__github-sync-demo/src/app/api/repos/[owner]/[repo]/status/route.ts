import { NextRequest, NextResponse } from "next/server";
import { trace } from "@opentelemetry/api";
import type { StatusResponse, ErrorResponse } from "@/types/api";

import {
  db,
  githubRepo,
  githubRepoDetails,
  githubRepoState,
  githubRepoCommit,
  githubRepoTrees,
  chromaSyncSources,
  chromaSyncInvocations,
} from "@/db";
import { eq, and, sql } from "drizzle-orm";
import { alias } from "drizzle-orm/pg-core";
import { validateEnv } from "@/lib/env";
import {
  ONE_MONTH_MS,
  ONE_DAY_MS,
  STATUS_UPDATE_THRESHOLD_MS,
  isTerminalStatus,
} from "@/lib/constants";
import type { GitHubTree } from "@/types/github";
import {
  refreshRepo,
  refreshCommit,
  refreshTree,
} from "@/services/github/cache";
import {
  refreshSource,
  refreshInvocation,
  refreshInvocationStatus,
} from "@/services/chroma/cache";

const tracer = trace.getTracer("api");

validateEnv();

function isStale(fetchedAt: Date, maxAge: number): boolean {
  return Date.now() - fetchedAt.getTime() > maxAge;
}

function getRepoName(owner: string, repo: string): string {
  return `${owner}/${repo}`;
}

interface CurrentState {
  repo: typeof githubRepo.$inferSelect | null;
  repoDetails: typeof githubRepoDetails.$inferSelect | null;
  state: typeof githubRepoState.$inferSelect | null;
  latestCommit: typeof githubRepoCommit.$inferSelect | null;
  latestProcessedCommit: typeof githubRepoCommit.$inferSelect | null;
  tree: typeof githubRepoTrees.$inferSelect | null;
  source: typeof chromaSyncSources.$inferSelect | null;
  invocation: typeof chromaSyncInvocations.$inferSelect | null;
}

async function getCurrentState(
  owner: string,
  repo: string,
): Promise<CurrentState> {
  const repoName = getRepoName(owner, repo);
  const processedCommit = alias(githubRepoCommit, "processed_commit");

  const result = await db
    .select({
      repo: githubRepo,
      repoDetails: githubRepoDetails,
      state: githubRepoState,
      commit: githubRepoCommit,
      processedCommit: processedCommit,
      tree: githubRepoTrees,
      source: chromaSyncSources,
      invocation: chromaSyncInvocations,
    })
    .from(githubRepo)
    .leftJoin(githubRepoDetails, eq(githubRepoDetails.name, githubRepo.name))
    .leftJoin(githubRepoState, eq(githubRepoState.repoName, githubRepo.name))
    .leftJoin(
      githubRepoCommit,
      eq(githubRepoCommit.sha, githubRepoState.latestCommitSha),
    )
    .leftJoin(
      processedCommit,
      eq(processedCommit.sha, githubRepoState.latestProcessedCommitSha),
    )
    .leftJoin(
      githubRepoTrees,
      and(
        eq(githubRepoTrees.repoName, githubRepoCommit.repoName),
        eq(githubRepoTrees.treeSha, githubRepoCommit.treeSha),
      ),
    )
    .leftJoin(
      chromaSyncSources,
      eq(chromaSyncSources.repoName, githubRepo.name),
    )
    .leftJoin(
      chromaSyncInvocations,
      sql`${chromaSyncInvocations.uuid} = (
        SELECT i2.invocation_uuid
        FROM chroma_sync_invocations i2
        WHERE i2.source_uuid = ${chromaSyncSources.uuid}
          AND i2.ref_identifier = ${githubRepoCommit.sha}
        ORDER BY i2.created_at DESC
        LIMIT 1
      )`,
    )
    .where(eq(githubRepo.name, repoName))
    .limit(1);

  const row = result[0];

  return {
    repo: row?.repo || null,
    repoDetails: row?.repoDetails || null,
    state: row?.state || null,
    latestCommit: row?.commit || null,
    latestProcessedCommit: row?.processedCommit || null,
    tree: row?.tree || null,
    source: row?.source || null,
    invocation: row?.invocation || null,
  };
}

// ============================================================================
// Response Formatting
// ============================================================================

function formatResponse(state: CurrentState): StatusResponse {
  const repoDetails = state.repoDetails;
  const isAvailable = state.repo?.available === true;

  let syncStatus: StatusResponse["sync_status"] = null;
  if (!state.state || !state.state.latestProcessedCommitSha) {
    syncStatus = "processing";
  } else if (
    state.state.latestCommitSha === state.state.latestProcessedCommitSha
  ) {
    syncStatus = "up_to_date";
  } else {
    syncStatus = "out_of_date";
  }

  const tree = (state.tree?.tree as GitHubTree["tree"]) ?? null;

  const latestCommit: StatusResponse["latest_commit"] = state.latestCommit
    ? {
        sha: state.latestCommit.sha,
        message: state.latestCommit.message,
        authorName: state.latestCommit.authorName,
        authorDate: state.latestCommit.authorDate,
        htmlUrl: state.latestCommit.htmlUrl,
      }
    : null;

  const latestProcessedCommit: StatusResponse["latest_processed_commit"] =
    state.latestProcessedCommit
      ? {
          sha: state.latestProcessedCommit.sha,
          message: state.latestProcessedCommit.message,
          authorName: state.latestProcessedCommit.authorName,
          authorDate: state.latestProcessedCommit.authorDate,
          htmlUrl: state.latestProcessedCommit.htmlUrl,
        }
      : null;

  return {
    exists: isAvailable,
    sync_status: syncStatus,
    is_private: repoDetails?.private ?? false,
    repo_info: repoDetails
      ? {
          fullName: state.repo?.name ?? "",
          description: repoDetails.description,
          htmlUrl: repoDetails.htmlUrl,
          language: repoDetails.language,
          stargazersCount: repoDetails.stargazersCount,
          forksCount: repoDetails.forksCount,
          watchersCount: repoDetails.watchersCount,
          openIssuesCount: repoDetails.openIssuesCount,
        }
      : null,
    latest_commit: latestCommit,
    latest_processed_commit: latestProcessedCommit,
    tree,
  };
}

// ============================================================================
// Main Handler
// ============================================================================

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ owner: string; repo: string }> },
): Promise<NextResponse<StatusResponse | ErrorResponse>> {
  const { owner, repo: repoName } = await params;
  const span = tracer.startSpan("api.repos.status");

  try {
    // Optimistically assume the repository exists and is fully indexed
    let state = await getCurrentState(owner, repoName);

    if (
      !state.repo ||
      state.repo.available === null ||
      isStale(state.repo.fetchedAt, ONE_MONTH_MS)
    ) {
      await refreshRepo(owner, repoName);
      state = await getCurrentState(owner, repoName);
    }

    if (!state.repo || state.repo.available === null) {
      return NextResponse.json(
        { error: `Did not update repository state` },
        { status: 500 },
      );
    }

    if (state.repo.available === false) {
      return NextResponse.json(
        {
          error: `Repository ${owner}/${repoName} not found (last checked ${state.repo?.fetchedAt?.toISOString() ?? "never"})`,
        },
        { status: 404 },
      );
    }

    const needsRefresh = {
      commit:
        !state.state ||
        !state.state.latestCommitSha ||
        isStale(state.state.fetchedAt, ONE_DAY_MS),
      tree: state.latestCommit && (!state.tree || state.tree.tree === null),
      source: !state.source || (state.source && !state.source.uuid),
      invocation: state.latestCommit && state.source && !state.invocation,
      invocationStatus:
        state.invocation &&
        !isTerminalStatus(state.invocation.status) &&
        state.invocation.fetchedAt &&
        isStale(state.invocation.fetchedAt, STATUS_UPDATE_THRESHOLD_MS),
    };

    if (
      needsRefresh.commit &&
      state.repo?.available === true &&
      state.repoDetails?.defaultBranch
    ) {
      refreshCommit(owner, repoName, state.repoDetails.defaultBranch).catch(
        (err) => console.error("Failed to refresh commit:", err),
      );
    }
    if (needsRefresh.tree && state.latestCommit) {
      refreshTree(owner, repoName, state.latestCommit.treeSha).catch((err) =>
        console.error("Failed to refresh tree:", err),
      );
    }
    if (needsRefresh.source && state.repo?.available === true) {
      refreshSource(owner, repoName).catch((err) =>
        console.error("Failed to refresh source:", err),
      );
    }
    if (needsRefresh.invocation && state.latestCommit && state.source) {
      refreshInvocation(owner, repoName, state.latestCommit.sha).catch((err) =>
        console.error("Failed to refresh invocation:", err),
      );
    }
    if (needsRefresh.invocationStatus && state.invocation) {
      const updated = await refreshInvocationStatus(state.invocation);
      if (updated?.status && isTerminalStatus(updated?.status)) {
        await db
          .update(githubRepoState)
          .set({
            latestProcessedCommitSha: updated?.refIdentifier,
          })
          .where(eq(githubRepoState.repoName, `${owner}/${repoName}`));
      }
    }

    return NextResponse.json(formatResponse(state));
  } catch (error) {
    console.error("Failed to check repository status:", error);
    span.recordException(error as Error);
    const errorResponse: ErrorResponse = {
      error: "Failed to check repository status",
    };
    return NextResponse.json(errorResponse, { status: 500 });
  } finally {
    span.end();
  }
}
