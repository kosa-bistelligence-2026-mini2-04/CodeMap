import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/Footer", () => ({
    default: () => null,
}));

import { metadata } from "./page";

describe("blog index metadata", () => {
    it("uses the blog marketing OG card", () => {
        expect(metadata.title).toBe("Engineering Insights for Repository Analysis and Security");
        expect(metadata.description).toContain("GitHub repository analysis");
        expect(metadata.openGraph?.title).toBe("RepoMind Engineering Insights");
        expect(metadata.openGraph?.images?.[0]?.url).toBe("/og/blogs.png");
    });
});
