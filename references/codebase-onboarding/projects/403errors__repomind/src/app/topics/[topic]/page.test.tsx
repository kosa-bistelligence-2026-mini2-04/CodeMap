import { beforeEach, describe, expect, it, vi } from "vitest";

const {
    getReposForTopicMock,
    isIndexableTopicMock,
} = vi.hoisted(() => ({
    getReposForTopicMock: vi.fn(),
    isIndexableTopicMock: vi.fn(),
}));

vi.mock("@/lib/repo-catalog", () => ({
    getReposForTopic: getReposForTopicMock,
    isIndexableTopic: isIndexableTopicMock,
}));

import { generateMetadata } from "./page";

describe("topic metadata", () => {
    beforeEach(() => {
        getReposForTopicMock.mockReset();
        isIndexableTopicMock.mockReset();
    });

    it("builds a topic card for indexable topics", async () => {
        isIndexableTopicMock.mockResolvedValue(true);
        getReposForTopicMock.mockResolvedValue([
            { owner: "acme", repo: "widget", stars: 1000, description: "Widget", topics: ["security"], language: "TypeScript" },
            { owner: "foo", repo: "bar", stars: 200, description: "Bar", topics: ["security"], language: "Go" },
        ]);

        const metadata = await generateMetadata({
            params: Promise.resolve({ topic: "security" }),
        });

        expect(metadata.title).toBe("Best Open Source Security Repositories");
        expect(metadata.robots?.index).toBe(true);
        expect(metadata.openGraph?.images?.[0]?.url).toBe("/og/trending-topics.png");
    });

    it("marks non-indexable topics as noindex", async () => {
        isIndexableTopicMock.mockResolvedValue(false);
        getReposForTopicMock.mockResolvedValue([]);

        const metadata = await generateMetadata({
            params: Promise.resolve({ topic: "internal-tools" }),
        });

        expect(metadata.robots?.index).toBe(false);
        expect(metadata.openGraph?.images?.[0]?.url).toBe("/og/trending-topics.png");
    });
});
