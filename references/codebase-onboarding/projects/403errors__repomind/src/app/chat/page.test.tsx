import { describe, expect, it, vi } from "vitest";

vi.mock("./ChatPageClient", () => ({
    default: () => null,
}));

import { metadata } from "./page";

describe("chat metadata", () => {
    it("uses a generic, noindex chat preview card", () => {
        expect(metadata.title).toBe("Chat");
        expect(metadata.description).toContain("Paste a GitHub repository or developer profile");
        expect(metadata.robots?.index).toBe(false);
        expect(metadata.robots?.follow).toBe(true);
        expect(metadata.openGraph?.images?.[0]?.url).toBe("/og/homepage.png");
        expect(metadata.twitter?.images?.[0]).toBe("/og/homepage.png");
    });
});
