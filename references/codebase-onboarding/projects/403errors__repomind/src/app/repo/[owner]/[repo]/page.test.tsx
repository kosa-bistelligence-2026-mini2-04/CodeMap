import { beforeEach, describe, expect, it, vi } from "vitest";

const {
    isCuratedRepoMock,
    getCachedRepoUnavailableMock,
} = vi.hoisted(() => ({
    isCuratedRepoMock: vi.fn(),
    getCachedRepoUnavailableMock: vi.fn(),
}));

vi.mock("@/lib/github", () => ({
    getRepoFullContext: vi.fn(),
}));

vi.mock("@/lib/repo-catalog", () => ({
    isCuratedRepo: isCuratedRepoMock,
}));

vi.mock("@/lib/cache", () => ({
    cacheRepoUnavailable: vi.fn(),
    getCachedRepoUnavailable: getCachedRepoUnavailableMock,
}));

import { generateMetadata } from "./page";

describe("repository metadata", () => {
    beforeEach(() => {
        isCuratedRepoMock.mockReset();
        getCachedRepoUnavailableMock.mockReset();
    });

    it("builds branded metadata for indexed repositories", async () => {
        getCachedRepoUnavailableMock.mockResolvedValue(false);
        isCuratedRepoMock.mockResolvedValue(true);

        const metadata = await generateMetadata({
            params: Promise.resolve({ owner: "acme", repo: "widget" }),
        });

        expect(metadata.title).toBe("acme/widget");
        expect(metadata.robots?.index).toBe(true);
        expect(metadata.openGraph?.images?.[0]?.url).toBe("/og/repository-analysis.png");
    });
});
