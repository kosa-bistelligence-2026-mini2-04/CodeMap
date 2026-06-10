import type { GitHubTree } from "./github";

export interface RepoInfo {
  fullName: string;
  description: string | null;
  htmlUrl: string;
  language: string | null;
  stargazersCount: number;
  forksCount: number;
  watchersCount: number;
  openIssuesCount: number;
}

export type RepoSyncStatus =
  | "processing"
  | "out_of_date"
  | "up_to_date"
  | "failed";

export interface SyncResponse {
  status: RepoSyncStatus;
}

export interface CommitInfo {
  sha: string;
  message: string;
  authorName: string | null;
  authorDate: Date | null;
  htmlUrl: string;
}

export interface StatusResponse {
  exists: boolean;
  sync_status: RepoSyncStatus | null;
  is_private: boolean;
  repo_info: RepoInfo | null;
  latest_commit: CommitInfo | null;
  latest_processed_commit: CommitInfo | null;
  tree: GitHubTree["tree"] | null;
}

export interface ErrorResponse {
  error: string;
}
