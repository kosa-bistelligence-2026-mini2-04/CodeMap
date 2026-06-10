export interface GitHubRepo {
  type: "repo";

  name: string;
  description: string | null;
  defaultBranch: string;
  htmlUrl: string;
  language: string | null;
  stargazersCount: number;
  forksCount: number;
  watchersCount: number;
  openIssuesCount: number;
  subscribersCount: number;
  fork: boolean;
  private: boolean;
  licenseName: string | null;
}

export interface GitHubCommit {
  type: "commit";

  sha: string;
  treeSha: string;
  message: string;
  authorName: string;
  authorDate: Date;
  htmlUrl: string;
}

export interface GitHubTree {
  type: "tree";

  sha: string;
  url?: string;
  tree: Array<{
    path: string;
    mode: string;
    type: string;
    size?: number;
    sha: string;
    url?: string;
  }>;
  truncated: boolean;
}

export interface GitHubError {
  type: "error";

  private?: boolean;
  accessible?: boolean;
  notFound?: boolean;
}

export interface TreeNode {
  name: string;
  type: "directory" | "file";
  size?: string;
  children?: TreeNode[];
}

export interface SearchResult {
  output_mode: string;
  result: {
    content: string;
    filename_sha256: string;
    file_path: string;
    language: string;
    start_line: number;
    end_line: number;
  };
}

export interface CodeSnippet {
  content: string;
  start_line: number;
  end_line: number;
}

export interface GroupedSearchResult {
  filename_sha256: string;
  file_path: string;
  language: string;
  snippets: CodeSnippet[];
}

export interface SearchResultsData {
  version_used: string;
  results: SearchResult[];
  truncation_message?: string;
}

export interface ReadFileResult {
  version_used: string;
  file_path: string;
  start_line: number;
  end_line: number;
  content: string;
  total_lines: number;
}
