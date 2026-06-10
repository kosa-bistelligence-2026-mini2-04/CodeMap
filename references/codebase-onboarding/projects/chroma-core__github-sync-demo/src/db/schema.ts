import {
  boolean,
  index,
  integer,
  jsonb,
  pgEnum,
  pgTable,
  primaryKey,
  serial,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";

export const githubRepo = pgTable("github_repo", {
  // name = owner/repo
  name: text("name").notNull().primaryKey(),

  fetchedAt: timestamp("fetched_at").notNull().defaultNow(),

  // null = not fetched yet
  // true = available
  // false = not available -- does not exist, inaccessible, etc.
  available: boolean("available"),
});

// Exists only if the repo is available
export const githubRepoDetails = pgTable("github_repo_details", {
  name: text("name")
    .notNull()
    .primaryKey()
    .references(() => githubRepo.name, { onDelete: "cascade" }),

  description: text("description").notNull(),
  defaultBranch: text("default_branch").notNull(),
  htmlUrl: text("html_url").notNull(),
  language: text("language").notNull(),
  stargazersCount: integer("stargazers_count").notNull(),
  forksCount: integer("forks_count").notNull(),
  watchersCount: integer("watchers_count").notNull(),
  openIssuesCount: integer("open_issues_count").notNull(),
  subscribersCount: integer("subscribers_count").notNull(),
  fork: boolean("fork").notNull(),
  private: boolean("private").notNull(),
  licenseName: text("license_name"),
  createdAt: timestamp("created_at").notNull(),
});

export const githubRepoState = pgTable("github_repo_state", {
  repoName: text("repo_name")
    .notNull()
    .primaryKey()
    .references(() => githubRepo.name, { onDelete: "cascade" }),

  // Current commit SHA of HEAD from GET /repos/{owner}/{repo}/branches/{branch}
  latestCommitSha: text("latest_commit_sha").references(
    () => githubRepoCommit.sha,
  ),

  // Latest commit that has a completed invocation
  latestProcessedCommitSha: text("latest_processed_commit_sha").references(
    () => githubRepoCommit.sha,
  ),

  fetchedAt: timestamp("fetched_at").defaultNow().notNull(),
});

// Unlike the other tables, this table does not need to be able to
// have a placeholder because we never fetch a commit by its SHA
// and have to protect against race conditions.
export const githubRepoCommit = pgTable(
  "github_repo_commit",
  {
    sha: text("sha").primaryKey(),
    repoName: text("repo_name")
      .notNull()
      .references(() => githubRepo.name, { onDelete: "cascade" }),

    // From the github API
    treeSha: text("tree_sha").notNull(),
    message: text("message").notNull(),
    authorName: text("author_name"),
    authorDate: timestamp("author_date"),
    htmlUrl: text("html_url").notNull(),

    fetchedAt: timestamp("fetched_at").defaultNow().notNull(),
  },
  (table) => ({
    repoNameIdx: index("github_repo_commit_repo_name_idx").on(table.repoName),
  }),
);

export const githubRepoTrees = pgTable(
  "github_repo_trees",
  {
    treeSha: text("tree_sha").primaryKey(),
    repoName: text("repo_name")
      .notNull()
      .references(() => githubRepo.name, { onDelete: "cascade" }),

    tree: jsonb("tree"), // null = not fetched yet

    fetchedAt: timestamp("fetched_at").defaultNow().notNull(),
  },
  (table) => ({
    repoNameIdx: index("github_repo_trees_repo_name_idx").on(table.repoName),
  }),
);

// One repo can have multiple chroma sync sources.
export const chromaSyncSources = pgTable(
  "chroma_sync_sources",
  {
    id: serial("id").primaryKey(),
    repoName: text("repo_name")
      .notNull()
      .references(() => githubRepo.name, { onDelete: "cascade" }),

    // Nullable because we want to use a placeholder row
    uuid: uuid("source_uuid").unique(),

    createdAt: timestamp("created_at").defaultNow().notNull(),
  },
  (table) => ({
    repoNameIdx: uniqueIndex("chroma_sync_sources_repo_name_idx").on(
      table.repoName,
    ),
  }),
);

export const chromaSyncInvocationStatus = pgEnum(
  "chroma_sync_invocation_status",
  ["pending", "processing", "cancelled", "completed", "failed"],
);

// One source can have multiple invocations.
export const chromaSyncInvocations = pgTable(
  "chroma_sync_invocations",
  {
    id: serial("id").primaryKey(),
    sourceUuid: uuid("source_uuid")
      .notNull()
      .references(() => chromaSyncSources.uuid, { onDelete: "cascade" }),
    refIdentifier: text("ref_identifier").notNull(), // SHA of the commit
    targetCollectionName: text("target_collection_name").notNull(),

    // Nullable because we want to use a placeholder row
    uuid: uuid("invocation_uuid").unique(),
    status: chromaSyncInvocationStatus("status").default("pending"),

    createdAt: timestamp("created_at").defaultNow().notNull(),
    fetchedAt: timestamp("fetched_at").defaultNow().notNull(),
  },
  (table) => ({
    sourceUuidIdx: index("chroma_sync_invocations_source_uuid_idx").on(
      table.sourceUuid,
    ),
    refIdentifierIdx: index("chroma_sync_invocations_ref_identifier_idx").on(
      table.refIdentifier,
    ),
    sourceRefUnique: uniqueIndex(
      "chroma_sync_invocations_source_ref_unique",
    ).on(table.sourceUuid, table.refIdentifier),
  }),
);
