// Client for directly accessing the Github API

import { env } from "@/lib/env";
import type {
  GitHubCommit,
  GitHubError,
  GitHubRepo,
  GitHubTree,
} from "@/types/github";
import { trace } from "@opentelemetry/api";
import { Octokit } from "octokit";

const tracer = trace.getTracer("github");

const octokit = new Octokit({
  auth: env.GITHUB_TOKEN,
});

export async function getRepository(
  owner: string,
  repo: string,
): Promise<GitHubRepo | GitHubError> {
  const span = tracer.startSpan("github.getRepository");

  try {
    const response = await octokit.request("GET /repos/{owner}/{repo}", {
      owner,
      repo,
      headers: {
        "X-GitHub-Api-Version": "2022-11-28",
      },
    });

    const data = response.data;

    return {
      type: "repo",

      name: data.full_name,
      description: data.description,
      defaultBranch: data.default_branch,
      htmlUrl: data.html_url,
      language: data.language,
      stargazersCount: data.stargazers_count,
      forksCount: data.forks_count,
      watchersCount: data.watchers_count,
      openIssuesCount: data.open_issues_count,
      subscribersCount: data.subscribers_count || 0,
      fork: data.fork,
      private: data.private,
      licenseName: data.license?.name || null,
    };
  } catch (error: any) {
    if (error.status === 404) {
      span.setAttribute("error.type", "not_found");
      return { type: "error", notFound: true };
    }

    if (error.status === 403) {
      span.setAttribute("error.type", "private_inaccessible");
      return { type: "error", private: true, accessible: false };
    }

    span.recordException(error);
    throw error;
  } finally {
    span.end();
  }
}

export async function getBranchCommit(
  owner: string,
  repo: string,
  branch: string,
): Promise<GitHubCommit | null> {
  const span = tracer.startSpan("github.getBranchCommit");

  try {
    const response = await octokit.request(
      "GET /repos/{owner}/{repo}/branches/{branch}",
      {
        owner,
        repo,
        branch,
        headers: {
          "X-GitHub-Api-Version": "2022-11-28",
        },
      },
    );

    const commitData = response.data.commit;
    const treeSha = commitData.commit.tree.sha;

    return {
      type: "commit",
      sha: commitData.sha,
      treeSha,
      message: commitData.commit.message,
      authorName: commitData.commit.author?.name || "Unknown",
      authorDate: new Date(commitData.commit.author?.date || Date.now()),
      htmlUrl: commitData.html_url,
    };
  } catch (error: any) {
    if (error.status === 404) {
      span.setAttribute("error.type", "branch_not_found");
      return null;
    }

    span.recordException(error);
    throw error;
  } finally {
    span.end();
  }
}

export async function getRepositoryTree(
  owner: string,
  repo: string,
  treeSha: string,
  recursive: boolean = true,
): Promise<GitHubTree | null> {
  const span = tracer.startSpan("github.getRepositoryTree");

  try {
    const response = await octokit.request(
      "GET /repos/{owner}/{repo}/git/trees/{tree_sha}",
      {
        owner,
        repo,
        tree_sha: treeSha,
        recursive: recursive ? "true" : "false",
        headers: {
          "X-GitHub-Api-Version": "2022-11-28",
        },
      },
    );

    const data = response.data;

    span.setAttribute("tree.entries_count", data.tree?.length || 0);

    return { type: "tree", ...data };
  } catch (error: any) {
    if (error.status === 404) {
      span.setAttribute("error.type", "tree_not_found");
      return null;
    }

    if (error.status === 403) {
      span.setAttribute("error.type", "private_inaccessible");
      return null;
    }

    span.recordException(error);
    throw error;
  } finally {
    span.end();
  }
}
