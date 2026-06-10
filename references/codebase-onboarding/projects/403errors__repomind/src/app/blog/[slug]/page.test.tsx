import { beforeEach, describe, expect, it, vi } from "vitest";

const {
    getPublishedPostBySlugMock,
    getPublishedPostsMock,
} = vi.hoisted(() => ({
    getPublishedPostBySlugMock: vi.fn(),
    getPublishedPostsMock: vi.fn(),
}));

vi.mock("@/lib/services/blog-service", () => ({
    getPublishedPostBySlug: getPublishedPostBySlugMock,
    getPublishedPosts: getPublishedPostsMock,
}));

vi.mock("@/components/Footer", () => ({
    default: () => null,
}));

vi.mock("@/components/EnhancedMarkdown", () => ({
    EnhancedMarkdown: () => null,
}));

vi.mock("next/image", () => ({
    default: () => null,
}));

import { generateMetadata } from "./page";

describe("blog post metadata", () => {
    beforeEach(() => {
        getPublishedPostBySlugMock.mockReset();
        getPublishedPostsMock.mockReset();
    });

    it("builds article metadata for published posts", async () => {
        const post = {
            slug: "deep-dive",
            title: "Deep Dive into RepoMind",
            excerpt: "How we build high-context repository analysis for the web.",
            keywords: "security, analysis",
            category: "Engineering",
            image: "https://cdn.example.com/blog/deep-dive.png",
            author: "RepoMind",
            createdAt: new Date("2026-03-10T00:00:00.000Z"),
            updatedAt: new Date("2026-03-12T00:00:00.000Z"),
            publishedAt: new Date("2026-03-11T00:00:00.000Z"),
        };

        getPublishedPostBySlugMock.mockResolvedValue(post);

        const metadata = await generateMetadata({
            params: Promise.resolve({ slug: "deep-dive" }),
        });

        expect(metadata.title).toBe(post.title);
        expect(metadata.description).toBe(post.excerpt);
        expect(metadata.openGraph?.type).toBe("article");
        expect(metadata.openGraph?.publishedTime).toBe(post.publishedAt.toISOString());
        expect(metadata.openGraph?.modifiedTime).toBe(post.updatedAt.toISOString());
        expect(metadata.openGraph?.images?.[0]?.url).toBe("/og/blogs.png");
        expect(metadata.twitter?.images?.[0]).toBe(post.image);
    });

    it("returns noindex metadata for missing posts", async () => {
        getPublishedPostBySlugMock.mockResolvedValue(null);

        const metadata = await generateMetadata({
            params: Promise.resolve({ slug: "missing" }),
        });

        expect(metadata.title).toBe("Post Not Found");
        expect(metadata.robots?.index).toBe(false);
        expect(metadata.openGraph?.images?.[0]?.url).toBe("/og/homepage.png");
    });
});
