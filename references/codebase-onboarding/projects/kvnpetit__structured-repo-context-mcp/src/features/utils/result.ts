/**
 * Result building utilities for features
 *
 * Provides consistent result construction patterns
 */
import type { FeatureResult } from "@features/types";

/**
 * Create an error result with consistent formatting
 *
 * @param action - Description of what failed (e.g., "parse file", "execute query")
 * @param error - The error that occurred
 * @returns FeatureResult with success: false
 */
export function errorResult(action: string, error: unknown): FeatureResult {
  const message = error instanceof Error ? error.message : String(error);
  return {
    success: false,
    error: `Failed to ${action}: ${message}`,
  };
}

/**
 * Create a simple error result with a custom message
 *
 * @param error - The error message
 * @returns FeatureResult with success: false
 */
export function errorMessage(error: string): FeatureResult {
  return {
    success: false,
    error,
  };
}

/**
 * Create a success result with data and optional message
 *
 * @param data - The data to return
 * @param message - Optional success message
 * @returns FeatureResult with success: true
 */
export function successResult(data: unknown, message?: string): FeatureResult {
  return {
    success: true,
    data,
    message,
  };
}

/**
 * Create a success result with just a message (no data)
 *
 * @param message - The success message
 * @returns FeatureResult with success: true
 */
export function successMessage(message: string): FeatureResult {
  return {
    success: true,
    message,
  };
}
