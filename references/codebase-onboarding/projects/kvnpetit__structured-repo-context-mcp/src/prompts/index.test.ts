import { describe, expect, test, vi } from "vitest";
import { registerPrompts } from "@prompts";

describe("Prompt Registration", () => {
  test("registerPrompts does not throw", () => {
    const mockServer = {
      registerPrompt: vi.fn(),
    };

    expect(() => {
      registerPrompts(mockServer as never);
    }).not.toThrow();
  });

  test("registerPrompts registers 3 prompts", () => {
    const registerPromptMock = vi.fn();
    const mockServer = { registerPrompt: registerPromptMock };

    registerPrompts(mockServer as never);

    // Should register 3 prompts: src-overview, code-search-workflow, search-tips
    expect(registerPromptMock).toHaveBeenCalledTimes(3);
    expect(registerPromptMock).toHaveBeenCalledWith(
      "src-overview",
      expect.any(Object),
      expect.any(Function),
    );
    expect(registerPromptMock).toHaveBeenCalledWith(
      "code-search-workflow",
      expect.any(Object),
      expect.any(Function),
    );
    expect(registerPromptMock).toHaveBeenCalledWith(
      "search-tips",
      expect.any(Object),
      expect.any(Function),
    );
  });
});
