import { describe, expect, it } from "vitest";
import { metadata as solutionsMetadata } from "./solutions/page";
import { metadata as analysisMetadata } from "./github-repository-analysis/page";
import { metadata as reviewMetadata } from "./ai-code-review-tool/page";
import { metadata as securityMetadata } from "./security-scanner/page";

describe("solution page metadata", () => {
  it("uses unique, intent-led metadata titles", () => {
    const titles = [
      String(solutionsMetadata.title),
      String(analysisMetadata.title),
      String(reviewMetadata.title),
      String(securityMetadata.title),
    ];

    expect(new Set(titles).size).toBe(titles.length);
    expect(String(analysisMetadata.title)).toContain("GitHub Repository Analysis");
    expect(String(reviewMetadata.title)).toContain("AI Code Review Tool");
    expect(String(securityMetadata.title)).toContain("Repository Security Scanner");
  });

  it("keeps canonical URLs aligned to route paths", () => {
    expect(analysisMetadata.alternates?.canonical).toBe("/github-repository-analysis");
    expect(reviewMetadata.alternates?.canonical).toBe("/ai-code-review-tool");
    expect(securityMetadata.alternates?.canonical).toBe("/security-scanner");
    expect(solutionsMetadata.alternates?.canonical).toBe("/solutions");
  });
});
