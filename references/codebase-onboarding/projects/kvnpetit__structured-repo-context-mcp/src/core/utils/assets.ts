/**
 * Centralized asset directory utilities
 *
 * Provides consistent access to the assets directory and JSON config loading
 * across all core modules.
 */
import { existsSync, readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

/**
 * Cached assets directory path
 */
let assetsDirCache: string | null = null;

/**
 * Get the assets directory path
 *
 * Handles both ESM and CJS contexts by trying multiple possible paths
 * relative to the current module location.
 */
export function getAssetsDir(): string {
  if (assetsDirCache) {
    return assetsDirCache;
  }

  // Handle both ESM and CJS contexts
  const currentDir =
    typeof __dirname !== "undefined"
      ? __dirname
      : dirname(fileURLToPath(import.meta.url));

  // Try various paths relative to current file location
  const possiblePaths = [
    join(currentDir, "..", "..", "..", "assets"), // From dist/core/utils
    join(currentDir, "..", "..", "assets"), // From src/core/utils (dev)
    join(process.cwd(), "assets"), // From project root
  ];

  for (const p of possiblePaths) {
    if (existsSync(p)) {
      assetsDirCache = p;
      return p;
    }
  }

  // Default fallback
  assetsDirCache = join(process.cwd(), "assets");
  return assetsDirCache;
}

/**
 * Load and parse a JSON config file from the assets directory
 *
 * @param filename - Name of the JSON file in assets directory
 * @param defaultValue - Default value to return if file cannot be loaded
 * @returns Parsed JSON content or default value
 */
export function loadJsonConfig<T>(filename: string, defaultValue: T): T {
  const configPath = join(getAssetsDir(), filename);

  try {
    const content = readFileSync(configPath, "utf-8");
    return JSON.parse(content) as T;
  } catch {
    return defaultValue;
  }
}

/**
 * Get the path to a file within the assets directory
 *
 * @param segments - Path segments relative to assets directory
 * @returns Full path to the asset file
 */
export function getAssetPath(...segments: string[]): string {
  return join(getAssetsDir(), ...segments);
}

/**
 * Check if an asset file exists
 *
 * @param segments - Path segments relative to assets directory
 * @returns True if the file exists
 */
export function assetExists(...segments: string[]): boolean {
  return existsSync(getAssetPath(...segments));
}

/**
 * Clear the assets directory cache (for testing)
 */
export function clearAssetsDirCache(): void {
  assetsDirCache = null;
}
