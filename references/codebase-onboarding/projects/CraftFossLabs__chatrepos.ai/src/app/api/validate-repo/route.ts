import { NextResponse } from "next/server";
import { GitHubService } from "@/lib/github/github-service";
import { extractRepoInfo, isValidGitHubUrl } from "@/lib/utils";

export async function POST(request: Request) {
  try {
    const { url } = await request.json();

    // Basic URL validation
    if (!url || typeof url !== "string") {
      return NextResponse.json(
        { error: "Invalid request. URL is required." },
        { status: 400 }
      );
    }

    // Validate GitHub URL format
    if (!isValidGitHubUrl(url)) {
      return NextResponse.json(
        { error: "Invalid GitHub repository URL format." },
        { status: 400 }
      );
    }

    // Extract owner and repo from URL
    const repoInfo = extractRepoInfo(url);
    if (!repoInfo) {
      return NextResponse.json(
        { error: "Could not extract repository information from URL." },
        { status: 400 }
      );
    }

    // Check if repository exists and is accessible
    const githubService = new GitHubService();
    const isValid = await githubService.validateRepo(
      repoInfo.owner,
      repoInfo.repo
    );

    if (!isValid) {
      return NextResponse.json(
        { error: "Repository not found or not accessible." },
        { status: 404 }
      );
    }

    return NextResponse.json(
      { 
        valid: true,
        owner: repoInfo.owner,
        repo: repoInfo.repo
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("Error validating repository:", error);
    return NextResponse.json(
      { error: "Failed to validate repository." },
      { status: 500 }
    );
  }
}
