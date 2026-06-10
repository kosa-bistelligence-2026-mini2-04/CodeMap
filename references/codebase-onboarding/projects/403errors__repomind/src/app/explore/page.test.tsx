import { describe, expect, it } from "vitest";
import { metadata, livePages } from "./page";

describe("explore page", () => {
  it("uses discovery-focused metadata", () => {
    expect(metadata.title).toBe("Explore GitHub Analysis and Security Workflows");
    expect(metadata.description).toContain("Explore live RepoMind pages");
  });

  it("lists only live pages and avoids coming-soon slugs", () => {
    expect(livePages.length).toBeGreaterThanOrEqual(8);
    expect(livePages.some((item) => item.slug.includes("coming-soon"))).toBe(false);
  });
});
