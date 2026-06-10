import { NextResponse } from "next/server";
import { GitHubService } from "@/lib/github/github-service";
import { GeminiService } from "@/lib/gemini/gemini-service";
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

    try {
      console.log(`Analyzing repository: ${repoInfo.owner}/${repoInfo.repo}`);
      
      // Analyze repository
      const githubService = new GitHubService();
      const repoAnalysisData = await githubService.analyzeRepository(
        repoInfo.owner,
        repoInfo.repo
      );
      
      console.log("GitHub data fetched successfully");
      
      // Generate AI analysis
      const geminiService = new GeminiService();
      console.log("Sending data to Gemini for analysis...");
      const aiAnalysis = await geminiService.analyzeRepository(repoAnalysisData);
      
      console.log("AI analysis completed successfully");
      console.log("AI Summary:", aiAnalysis.summary);
      
      // Combine all data for response
      return NextResponse.json(
        {
          repoData: repoAnalysisData.repoData,
          repoContent: repoAnalysisData.repoContent,
          aiAnalysis,
        },
        { status: 200 }
      );
    } catch (error) {
      console.error("Error in repository analysis process:", error);
      return NextResponse.json(
        { error: `Analysis process failed: ${(error as Error).message}` },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error("Error analyzing repository:", error);
    return NextResponse.json(
      { error: "Failed to analyze repository." },
      { status: 500 }
    );
  }
}
