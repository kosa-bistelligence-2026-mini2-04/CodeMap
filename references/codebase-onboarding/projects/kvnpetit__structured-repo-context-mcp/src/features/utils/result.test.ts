import { describe, expect, test } from "vitest";

import {
  errorMessage,
  errorResult,
  successMessage,
  successResult,
} from "@features/utils";

describe("Result Utilities", () => {
  describe("errorResult", () => {
    test("creates error result from Error object", () => {
      const error = new Error("Something went wrong");
      const result = errorResult("parse file", error);

      expect(result.success).toBe(false);
      expect(result.error).toBe("Failed to parse file: Something went wrong");
    });

    test("creates error result from string", () => {
      const result = errorResult("execute query", "Invalid syntax");

      expect(result.success).toBe(false);
      expect(result.error).toBe("Failed to execute query: Invalid syntax");
    });

    test("handles non-Error objects", () => {
      const result = errorResult("test", { message: "obj error" });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Failed to test:");
    });
  });

  describe("errorMessage", () => {
    test("creates error result with custom message", () => {
      const result = errorMessage("Custom error message");

      expect(result.success).toBe(false);
      expect(result.error).toBe("Custom error message");
    });
  });

  describe("successResult", () => {
    test("creates success result with data and message", () => {
      const data = { count: 10, items: [] };
      const result = successResult(data, "Found 10 items");

      expect(result.success).toBe(true);
      expect(result.data).toEqual(data);
      expect(result.message).toBe("Found 10 items");
    });

    test("creates success result with data only", () => {
      const data = { value: 42 };
      const result = successResult(data);

      expect(result.success).toBe(true);
      expect(result.data).toEqual(data);
      expect(result.message).toBeUndefined();
    });

    test("handles undefined data", () => {
      const result = successResult(undefined, "Operation completed");

      expect(result.success).toBe(true);
      expect(result.data).toBeUndefined();
      expect(result.message).toBe("Operation completed");
    });
  });

  describe("successMessage", () => {
    test("creates success result with message only", () => {
      const result = successMessage("Operation successful");

      expect(result.success).toBe(true);
      expect(result.message).toBe("Operation successful");
      expect(result.data).toBeUndefined();
    });
  });
});
