import {
  db,
  chromaSyncSources,
  chromaSyncInvocations,
  githubRepoState,
} from "@/db";
import { eq, and, isNull, lt, SQL, isNotNull } from "drizzle-orm";
import { createSource, createInvocation, getInvocationStatus } from "./sync";
import { randomUUID } from "crypto";
import { STATUS_UPDATE_THRESHOLD_MS, isTerminalStatus } from "@/lib/constants";

export async function refreshSource(
  owner: string,
  repo: string,
): Promise<typeof chromaSyncSources.$inferSelect | null> {
  const repoName = `${owner}/${repo}`;

  // Optimistically check if source already exists
  const existingSource = await db
    .select({ source: chromaSyncSources })
    .from(chromaSyncSources)
    .where(
      and(
        eq(chromaSyncSources.repoName, repoName),
        isNotNull(chromaSyncSources.uuid),
      ),
    )
    .limit(1);

  const source = existingSource[0]?.source;
  if (source && source.uuid) {
    return source;
  }

  // Source does not exist, must be created

  // Idempotently insert placeholder row
  await db
    .insert(chromaSyncSources)
    .values({
      repoName,
      uuid: null,
    })
    .onConflictDoNothing();

  const result = await db.transaction(async (tx) => {
    const res = await tx
      .select({ source: chromaSyncSources })
      .from(chromaSyncSources)
      .where(
        and(
          eq(chromaSyncSources.repoName, repoName),
          isNull(chromaSyncSources.uuid),
        ),
      )
      .for("update", { skipLocked: true });

    if (res.length > 0) {
      const created = await createSource(owner, repo);

      const updated = await tx
        .update(chromaSyncSources)
        .set({ uuid: created.source_id })
        .where(eq(chromaSyncSources.repoName, repoName))
        .returning();

      return updated[0];
    }
    return null;
  });

  if (result !== null) {
    return result;
  }

  const current = await db
    .select({ source: chromaSyncSources })
    .from(chromaSyncSources)
    .where(eq(chromaSyncSources.repoName, repoName))
    .limit(1);

  return current[0]?.source || null;
}

export async function refreshInvocation(
  owner: string,
  repo: string,
  commitSha: string,
): Promise<typeof chromaSyncInvocations.$inferSelect | null> {
  const repoName = `${owner}/${repo}`;

  const sourceResult = await db
    .select({ source: chromaSyncSources })
    .from(chromaSyncSources)
    .where(eq(chromaSyncSources.repoName, repoName))
    .limit(1);

  const source = sourceResult[0]?.source;
  if (!source?.uuid) {
    return null;
  }

  const sourceUuid = source.uuid;
  const collectionName = randomUUID();

  await db
    .insert(chromaSyncInvocations)
    .values({
      sourceUuid,
      refIdentifier: commitSha,
      targetCollectionName: collectionName,
      uuid: null,
      status: "pending",
    })
    .onConflictDoNothing();

  const result = await db.transaction(async (tx) => {
    const isFirstFetch = isNull(chromaSyncInvocations.uuid);
    const whereClause = and(
      eq(chromaSyncInvocations.sourceUuid, sourceUuid),
      eq(chromaSyncInvocations.refIdentifier, commitSha),
      isFirstFetch,
    )!;

    const res = await tx
      .select({ invocation: chromaSyncInvocations })
      .from(chromaSyncInvocations)
      .where(whereClause)
      .for("update", { skipLocked: true });

    if (res.length > 0) {
      const created = await createInvocation(
        sourceUuid,
        commitSha,
        res[0].invocation.targetCollectionName,
      );

      const updated = await tx
        .update(chromaSyncInvocations)
        .set({
          uuid: created.invocation_id,
          fetchedAt: new Date(),
        })
        .where(eq(chromaSyncInvocations.id, res[0].invocation.id))
        .returning();

      return updated[0];
    }
    return null;
  });

  if (result !== null) {
    return result;
  }

  const current = await db
    .select({ invocation: chromaSyncInvocations })
    .from(chromaSyncInvocations)
    .where(
      and(
        eq(chromaSyncInvocations.sourceUuid, sourceUuid),
        eq(chromaSyncInvocations.refIdentifier, commitSha),
      ),
    )
    .for("update")
    .limit(1);

  return current[0]?.invocation || null;
}

export async function refreshInvocationStatus(
  invocation: typeof chromaSyncInvocations.$inferSelect,
  TTL: number = STATUS_UPDATE_THRESHOLD_MS,
  force: boolean = false,
): Promise<typeof chromaSyncInvocations.$inferSelect | null> {
  if (!invocation.uuid) {
    return null;
  }

  if (isTerminalStatus(invocation.status) && !force) {
    return invocation;
  }

  const result = await db.transaction(async (tx) => {
    let whereClause: SQL<unknown>;
    if (force) {
      whereClause = eq(chromaSyncInvocations.id, invocation.id);
    } else {
      const isExpired = lt(
        chromaSyncInvocations.fetchedAt,
        new Date(Date.now() - TTL),
      );
      whereClause = and(
        eq(chromaSyncInvocations.id, invocation.id),
        isExpired,
      )!;
    }

    const res = await tx
      .select({ invocation: chromaSyncInvocations })
      .from(chromaSyncInvocations)
      .where(whereClause)
      .for("update", { skipLocked: true });

    if (res.length > 0 && res[0].invocation.uuid) {
      const status = await getInvocationStatus(res[0].invocation.uuid);

      const updated = await tx
        .update(chromaSyncInvocations)
        .set({
          status: status.status,
          fetchedAt: new Date(),
        })
        .where(eq(chromaSyncInvocations.id, invocation.id))
        .returning();

      return updated[0];
    }
    return null;
  });

  if (result !== null) {
    return result;
  }

  const current = await db
    .select({ invocation: chromaSyncInvocations })
    .from(chromaSyncInvocations)
    .where(eq(chromaSyncInvocations.id, invocation.id))
    .for("update")
    .limit(1);

  return current[0]?.invocation || null;
}
