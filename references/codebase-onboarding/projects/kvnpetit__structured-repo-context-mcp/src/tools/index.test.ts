import { describe, expect, test, vi } from "vitest";
import { registerTools } from "@tools";
import { features } from "@features";

describe("Tool Registration", () => {
  test("registers all features as tools", () => {
    const toolMock = vi.fn(
      (_name: string, _desc: string, _schema: unknown, _handler: unknown) => {
        // Mock implementation
      },
    );
    const mockServer = {
      tool: toolMock,
    };

    registerTools(mockServer as never);

    expect(toolMock).toHaveBeenCalledTimes(features.length);
  });

  test("tool names match feature names", () => {
    const registeredTools: string[] = [];
    const toolMock = vi.fn(
      (name: string, _desc: string, _schema: unknown, _handler: unknown) => {
        registeredTools.push(name);
      },
    );
    const mockServer = {
      tool: toolMock,
    };

    registerTools(mockServer as never);

    for (const feature of features) {
      expect(registeredTools).toContain(feature.name);
    }
  });

  test("tool descriptions are passed correctly", () => {
    const toolCalls: { name: string; description: string }[] = [];
    const toolMock = vi.fn(
      (
        name: string,
        description: string,
        _schema: unknown,
        _handler: unknown,
      ) => {
        toolCalls.push({ name, description });
      },
    );
    const mockServer = {
      tool: toolMock,
    };

    registerTools(mockServer as never);

    for (const feature of features) {
      const call = toolCalls.find((c) => c.name === feature.name);
      expect(call?.description).toBe(feature.description);
    }
  });
});
