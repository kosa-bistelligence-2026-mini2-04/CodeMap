import { describe, expect, test, vi, beforeEach } from "vitest";
import { featureToCittyCommand } from "@cli/adapter";
import { z } from "zod";
import type { Feature } from "@features/types";
import type { CommandMeta } from "citty";

describe("CLI Adapter", () => {
  let consoleSpy: {
    log: ReturnType<typeof vi.spyOn>;
    error: ReturnType<typeof vi.spyOn>;
  };
  let exitSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = {
      log: vi.spyOn(console, "log").mockImplementation(() => undefined),
      error: vi.spyOn(console, "error").mockImplementation(() => undefined),
    };
    exitSpy = vi
      .spyOn(process, "exit")
      .mockImplementation(() => undefined as never);
  });

  test("featureToCittyCommand converts feature to citty command", () => {
    const testSchema = z.object({
      message: z.string().describe("Test message"),
    });

    const testFeature: Feature<typeof testSchema> = {
      name: "test_feature",
      description: "Test feature description",
      schema: testSchema,
      execute: (input) => ({
        success: true,
        message: `Echo: ${input.message}`,
      }),
    };

    const command = featureToCittyCommand(testFeature);
    const meta = command.meta as CommandMeta;

    expect(meta.name).toBe("test_feature");
    expect(meta.description).toBe("Test feature description");
    expect(command.args).toBeDefined();
  });

  test("featureToCittyCommand handles features with multiple args", () => {
    const schema = z.object({
      name: z.string().describe("Name parameter"),
      count: z.string().optional().describe("Count parameter"),
    });

    const feature: Feature<typeof schema> = {
      name: "multi_arg_test",
      description: "Multi-arg test",
      schema,
      execute: () => ({ success: true }),
    };

    const command = featureToCittyCommand(feature);
    const meta = command.meta as CommandMeta;

    expect(meta.name).toBe("multi_arg_test");
    expect(command.args).toBeDefined();
  });

  test("run function handles successful sync result with message", () => {
    const schema = z.object({
      value: z.string(),
    });

    const feature: Feature<typeof schema> = {
      name: "sync_success",
      description: "Sync success test",
      schema,
      execute: () => ({
        success: true,
        message: "Operation completed",
      }),
    };

    const command = featureToCittyCommand(feature);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (command.run as (ctx: { args: any }) => void)({ args: { value: "test" } });

    expect(consoleSpy.log).toHaveBeenCalled();
  });

  test("run function handles successful sync result with data only", () => {
    const schema = z.object({
      value: z.string(),
    });

    const feature: Feature<typeof schema> = {
      name: "sync_data",
      description: "Sync data test",
      schema,
      execute: () => ({
        success: true,
        data: { key: "value" },
      }),
    };

    const command = featureToCittyCommand(feature);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (command.run as (ctx: { args: any }) => void)({ args: { value: "test" } });

    expect(consoleSpy.log).toHaveBeenCalled();
  });

  test("run function handles failed sync result", () => {
    const schema = z.object({
      value: z.string(),
    });

    const feature: Feature<typeof schema> = {
      name: "sync_fail",
      description: "Sync fail test",
      schema,
      execute: () => ({
        success: false,
        error: "Something went wrong",
      }),
    };

    const command = featureToCittyCommand(feature);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (command.run as (ctx: { args: any }) => void)({ args: { value: "test" } });

    expect(consoleSpy.error).toHaveBeenCalled();
    expect(exitSpy).toHaveBeenCalledWith(1);
  });

  test("run function handles failed sync result without error message", () => {
    const schema = z.object({
      value: z.string(),
    });

    const feature: Feature<typeof schema> = {
      name: "sync_fail_no_msg",
      description: "Sync fail no message test",
      schema,
      execute: () => ({
        success: false,
      }),
    };

    const command = featureToCittyCommand(feature);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (command.run as (ctx: { args: any }) => void)({ args: { value: "test" } });

    expect(consoleSpy.error).toHaveBeenCalled();
    expect(exitSpy).toHaveBeenCalledWith(1);
  });

  test("run function handles async result", async () => {
    const schema = z.object({
      value: z.string(),
    });

    const feature: Feature<typeof schema> = {
      name: "async_success",
      description: "Async success test",
      schema,
      execute: async () =>
        Promise.resolve({
          success: true,
          message: "Async done",
        }),
    };

    const command = featureToCittyCommand(feature);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (command.run as (ctx: { args: any }) => void)({ args: { value: "test" } });

    // Wait for promise to resolve
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(consoleSpy.log).toHaveBeenCalled();
  });

  test("run function handles async rejection with Error", async () => {
    const schema = z.object({
      value: z.string(),
    });

    const feature: Feature<typeof schema> = {
      name: "async_reject_error",
      description: "Async reject with Error test",
      schema,
      execute: async () => Promise.reject(new Error("Async failure")),
    };

    const command = featureToCittyCommand(feature);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (command.run as (ctx: { args: any }) => void)({ args: { value: "test" } });

    // Wait for promise to reject
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(consoleSpy.error).toHaveBeenCalled();
    expect(exitSpy).toHaveBeenCalledWith(1);
  });

  test("run function handles async rejection with non-Error", async () => {
    const schema = z.object({
      value: z.string(),
    });

    const feature: Feature<typeof schema> = {
      name: "async_reject_non_error",
      description: "Async reject with non-Error test",
      schema,
      // eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors
      execute: async () => Promise.reject("String error"),
    };

    const command = featureToCittyCommand(feature);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (command.run as (ctx: { args: any }) => void)({ args: { value: "test" } });

    // Wait for promise to reject
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(consoleSpy.error).toHaveBeenCalled();
    expect(exitSpy).toHaveBeenCalledWith(1);
  });
});
