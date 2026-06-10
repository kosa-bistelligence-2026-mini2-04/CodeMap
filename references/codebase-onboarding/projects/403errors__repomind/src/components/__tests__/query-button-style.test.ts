import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const chatInputSource = readFileSync(
    path.resolve(process.cwd(), "src/components/ChatInput.tsx"),
    "utf8"
);
const repoSearchSource = readFileSync(
    path.resolve(process.cwd(), "src/components/RepoSearch.tsx"),
    "utf8"
);

describe("query button modernized styling", () => {
    it("applies accessible focus-ring and active purple styling to chat send button", () => {
        expect(chatInputSource).toContain("focus-visible:ring-purple-500/60");
        expect(chatInputSource).toContain("bg-purple-500/10 text-purple-400 border-purple-500/20");
    });

    it("applies visible keyboard focus styling to repo search submit button", () => {
        expect(repoSearchSource).toContain("focus-visible:ring-1");
        expect(repoSearchSource).toContain("focus-visible:ring-white/10");
    });
});
