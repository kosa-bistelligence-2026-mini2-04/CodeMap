import { describe, expect, it } from "vitest";
import { footerLinks } from "./Footer";

describe("footer product links", () => {
  it("routes product links to live pages and not coming-soon", () => {
    const productLinks = footerLinks.product;
    expect(productLinks.length).toBeGreaterThanOrEqual(3);
    expect(productLinks.some((item) => item.href.includes("coming-soon"))).toBe(false);
    expect(productLinks.some((item) => item.href === "/github-repository-analysis")).toBe(true);
    expect(productLinks.some((item) => item.href === "/ai-code-review-tool")).toBe(true);
    expect(productLinks.some((item) => item.href === "/security-scanner")).toBe(true);
  });
});
