import { zodToCittyArgs } from "@cli/parser";
import { describe, expect, test } from "vitest";
import { z } from "zod";

describe("Zod to Citty Parser", () => {
  test("converts ZodString to citty arg", () => {
    const schema = z.object({
      name: z.string().describe("User name"),
    });

    const args = zodToCittyArgs(schema);

    expect(args.name).toBeDefined();
    expect(args.name?.type).toBe("string");
    expect(args.name?.description).toBe("User name");
    expect(args.name?.required).toBe(true);
  });

  test("converts optional ZodString to citty arg", () => {
    const schema = z.object({
      email: z.string().optional().describe("User email"),
    });

    const args = zodToCittyArgs(schema);
    expect(args.email).toBeDefined();
    expect(args.email?.type).toBe("string");
    expect(args.email?.required).toBe(false);
  });

  test("converts ZodBoolean to citty arg", () => {
    const schema = z.object({
      verbose: z.boolean().describe("Verbose output"),
    });

    const args = zodToCittyArgs(schema);

    expect(args.verbose).toBeDefined();
    expect(args.verbose?.type).toBe("boolean");
  });

  test("converts ZodBoolean with default to citty arg", () => {
    const schema = z.object({
      debug: z.boolean().default(false).describe("Debug mode"),
    });

    const args = zodToCittyArgs(schema);

    expect(args.debug).toBeDefined();
    expect(args.debug?.type).toBe("boolean");
    expect(args.debug?.default).toBe(false);
    expect(args.debug?.required).toBe(false);
  });

  test("converts ZodDefault to citty arg with default value", () => {
    const schema = z.object({
      format: z.string().default("text").describe("Output format"),
    });

    const args = zodToCittyArgs(schema);

    expect(args.format).toBeDefined();
    expect(args.format?.default).toBe("text");
    expect(args.format?.required).toBe(false);
  });

  test("handles ZodEnum as string", () => {
    const schema = z.object({
      level: z.enum(["info", "warn", "error"]).describe("Log level"),
    });

    const args = zodToCittyArgs(schema);

    expect(args.level).toBeDefined();
    expect(args.level?.type).toBe("string");
  });

  test("returns empty object for non-object schema", () => {
    const schema = z.string();

    const args = zodToCittyArgs(schema);

    expect(args).toEqual({});
  });

  test("handles optional with description on inner type", () => {
    const schema = z.object({
      port: z.number().describe("Port number").optional(),
    });

    const args = zodToCittyArgs(schema);

    expect(args.port).toBeDefined();
    expect(args.port?.description).toBe("Port number");
    expect(args.port?.required).toBe(false);
  });

  test("handles default with description on inner type", () => {
    const schema = z.object({
      host: z.string().describe("Hostname").default("localhost"),
    });

    const args = zodToCittyArgs(schema);

    expect(args.host).toBeDefined();
    expect(args.host?.description).toBe("Hostname");
    expect(args.host?.default).toBe("localhost");
  });

  test("handles ZodNumber as string type", () => {
    const schema = z.object({
      count: z.number().describe("Count value"),
    });

    const args = zodToCittyArgs(schema);

    expect(args.count).toBeDefined();
    expect(args.count?.type).toBe("string");
    expect(args.count?.description).toBe("Count value");
  });

  test("handles field without description", () => {
    const schema = z.object({
      value: z.string(),
    });

    const args = zodToCittyArgs(schema);

    expect(args.value).toBeDefined();
    expect(args.value?.type).toBe("string");
    expect(args.value?.description).toBeUndefined();
  });

  test("handles nested optional default patterns", () => {
    const schema = z.object({
      timeout: z.number().optional().default(30),
    });

    const args = zodToCittyArgs(schema);

    expect(args.timeout).toBeDefined();
    expect(args.timeout?.required).toBe(false);
  });

  test("handles schema without _def property", () => {
    // Create a mock schema-like object without _def
    const fakeSchema = {
      shape: {
        field: {}, // No _def, no description
      },
    };

    const args = zodToCittyArgs(fakeSchema as unknown as z.ZodType);

    expect(args.field).toBeDefined();
    expect(args.field?.type).toBe("string");
  });

  test("handles boolean without description", () => {
    const schema = z.object({
      flag: z.boolean(),
    });

    const args = zodToCittyArgs(schema);

    expect(args.flag).toBeDefined();
    expect(args.flag?.type).toBe("boolean");
    expect(args.flag?.description).toBeUndefined();
  });
});
