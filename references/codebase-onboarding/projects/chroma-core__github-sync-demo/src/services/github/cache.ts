import {
  db,
  githubRepo,
  githubRepoDetails,
  githubRepoState,
  githubRepoCommit,
  githubRepoTrees,
} from "@/db";
import { eq, gt, isNull, lt, or, and, SQL } from "drizzle-orm";
import { getRepository, getBranchCommit, getRepositoryTree } from "./client";
import { GitHubRepo } from "@/types/github";
import { ONE_MONTH_MS, ONE_DAY_MS } from "@/lib/constants";

export async function refreshRepo(
  owner: string,
  repo: string,
  TTL: number = ONE_MONTH_MS,
  force: boolean = false,
): Promise<GitHubRepo | null> {
  const repoName = `${owner}/${repo}`;
  // Idempotently insert placeholder row
  await db
    .insert(githubRepo)
    .values({
      name: repoName,
      available: null,
    })
    .onConflictDoNothing({ target: githubRepo.name });

  const result = await db.transaction(async (tx) => {
    let whereClause: SQL<unknown>;
    if (force) {
      whereClause = eq(githubRepo.name, repoName);
    } else {
      const isFirstFetch = isNull(githubRepo.available);
      const isExpired = lt(githubRepo.fetchedAt, new Date(Date.now() - TTL));
      whereClause = and(
        eq(githubRepo.name, repoName),
        or(isFirstFetch, isExpired),
      )!;
    }

    const res = await tx
      .select({
        repo: githubRepo,
      })
      .from(githubRepo)
      .where(whereClause)
      .for("update", { skipLocked: true });

    if (res.length > 0) {
      const fetched = await getRepository(owner, repo);
      switch (fetched.type) {
        case "repo": {
          const updateRepoPromise = tx
            .update(githubRepo)
            .set({ available: true, fetchedAt: new Date() })
            .where(eq(githubRepo.name, repoName));

          const newDetails = {
            description: fetched.description || "",
            defaultBranch: fetched.defaultBranch,
            htmlUrl: fetched.htmlUrl,
            language: fetched.language || "",
            stargazersCount: fetched.stargazersCount,
            forksCount: fetched.forksCount,
            watchersCount: fetched.watchersCount,
            openIssuesCount: fetched.openIssuesCount,
            subscribersCount: fetched.subscribersCount,
            fork: fetched.fork,
            private: fetched.private,
            licenseName: fetched.licenseName,
            createdAt: new Date(),
          };
          const updateRepoDetailsPromise = tx
            .insert(githubRepoDetails)
            .values({
              name: repoName,
              ...newDetails,
            })
            .onConflictDoUpdate({
              target: githubRepoDetails.name,
              set: newDetails,
            });
          await Promise.all([updateRepoPromise, updateRepoDetailsPromise]);
          return fetched;
        }
        case "error":
          await tx
            .update(githubRepo)
            .set({ available: false, fetchedAt: new Date() })
            .where(eq(githubRepo.name, repoName));
          return null;
      }
    }
    return null;
  });

  if (result !== null) {
    return result;
  }

  const current = await db
    .select({
      repo: githubRepo,
      details: githubRepoDetails,
    })
    .from(githubRepo)
    .leftJoin(githubRepoDetails, eq(githubRepoDetails.name, githubRepo.name))
    .where(eq(githubRepo.name, repoName))
    .for("update", { of: githubRepo })
    .limit(1);

  if (current.length === 0 || !current[0].repo.available) {
    return null;
  }

  const row = current[0];
  if (!row.details) {
    return null;
  }

  return {
    type: "repo" as const,
    name: row.repo.name,
    description: row.details.description || null,
    defaultBranch: row.details.defaultBranch,
    htmlUrl: row.details.htmlUrl,
    language: row.details.language || null,
    stargazersCount: row.details.stargazersCount,
    forksCount: row.details.forksCount,
    watchersCount: row.details.watchersCount,
    openIssuesCount: row.details.openIssuesCount,
    subscribersCount: row.details.subscribersCount,
    fork: row.details.fork,
    private: row.details.private,
    licenseName: row.details.licenseName,
  };
}

export async function refreshCommit(
  owner: string,
  repo: string,
  branch: string,
  TTL: number = ONE_DAY_MS,
  force: boolean = false,
): Promise<typeof githubRepoCommit.$inferSelect | null> {
  const repoName = `${owner}/${repo}`;
  // Idempotently insert placeholder row
  await db
    .insert(githubRepoState)
    .values({
      repoName,
      latestCommitSha: null,
      latestProcessedCommitSha: null,
    })
    .onConflictDoNothing({ target: githubRepoState.repoName });

  const result = await db.transaction(async (tx) => {
    let whereClause: SQL<unknown>;
    if (force) {
      whereClause = eq(githubRepoState.repoName, repoName);
    } else {
      const isFirstFetch = isNull(githubRepoState.latestCommitSha);
      const isExpired = lt(
        githubRepoState.fetchedAt,
        new Date(Date.now() - TTL),
      );
      whereClause = and(
        eq(githubRepoState.repoName, repoName),
        or(isFirstFetch, isExpired),
      )!;
    }

    const res = await tx
      .select({
        state: githubRepoState,
      })
      .from(githubRepoState)
      .where(whereClause)
      .for("update", { skipLocked: true });

    if (res.length > 0) {
      const fetched = await getBranchCommit(owner, repo, branch);

      if (!fetched) {
        return null;
      }

      const newCommit = {
        sha: fetched.sha,
        treeSha: fetched.treeSha,
        message: fetched.message,
        authorName: fetched.authorName,
        authorDate: fetched.authorDate,
        htmlUrl: fetched.htmlUrl,
      };

      const upsertCommitPromise = tx
        .insert(githubRepoCommit)
        .values({
          repoName,
          ...newCommit,
        })
        .onConflictDoUpdate({
          target: githubRepoCommit.sha,
          set: newCommit,
        })
        .returning();

      const updateStatePromise = tx
        .update(githubRepoState)
        .set({
          latestCommitSha: fetched.sha,
          fetchedAt: new Date(),
        })
        .where(eq(githubRepoState.repoName, repoName));

      const [commit] = await Promise.all([
        upsertCommitPromise,
        updateStatePromise,
      ]);
      return commit[0];
    }
    return null;
  });

  if (result !== null) {
    return result;
  }

  const current = await db
    .select({
      state: githubRepoState,
      commit: githubRepoCommit,
    })
    .from(githubRepoState)
    .leftJoin(
      githubRepoCommit,
      eq(githubRepoCommit.sha, githubRepoState.latestCommitSha),
    )
    .where(eq(githubRepoState.repoName, repoName))
    .for("update", { of: githubRepoState })
    .limit(1);

  return current[0]?.commit || null;
}

export async function refreshTree(
  owner: string,
  repo: string,
  treeSha: string,
  TTL: number = ONE_DAY_MS,
  force: boolean = false,
): Promise<typeof githubRepoTrees.$inferSelect | null> {
  const repoName = `${owner}/${repo}`;
  // Idempotently insert placeholder row
  await db
    .insert(githubRepoTrees)
    .values({
      repoName,
      treeSha,
      tree: null,
    })
    .onConflictDoNothing({ target: githubRepoTrees.treeSha });

  const result = await db.transaction(async (tx) => {
    let whereClause: SQL<unknown>;
    if (force) {
      whereClause = eq(githubRepoTrees.treeSha, treeSha);
    } else {
      const isFirstFetch = isNull(githubRepoTrees.tree);
      const isExpired = lt(
        githubRepoTrees.fetchedAt,
        new Date(Date.now() - TTL),
      );
      whereClause = and(
        eq(githubRepoTrees.treeSha, treeSha),
        or(isFirstFetch, isExpired),
      )!;
    }

    const res = await tx
      .select({
        tree: githubRepoTrees,
      })
      .from(githubRepoTrees)
      .where(whereClause)
      .for("update", { skipLocked: true });

    if (res.length > 0) {
      const fetched = await getRepositoryTree(owner, repo, treeSha);
      if (!fetched) {
        return null;
      }

      await tx
        .update(githubRepoTrees)
        .set({
          tree: fetched.tree,
          fetchedAt: new Date(),
        })
        .where(eq(githubRepoTrees.treeSha, treeSha));

      return {
        ...res[0].tree,
        tree: fetched.tree,
        fetchedAt: new Date(),
      };
    }
    return null;
  });

  if (result !== null) {
    return result;
  }

  const current = await db
    .select({
      tree: githubRepoTrees,
    })
    .from(githubRepoTrees)
    .where(eq(githubRepoTrees.treeSha, treeSha))
    .for("update")
    .limit(1);

  return current[0]?.tree || null;
}
