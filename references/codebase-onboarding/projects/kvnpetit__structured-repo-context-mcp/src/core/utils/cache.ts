/**
 * Centralized cache management
 *
 * Provides a registry for cache clear functions across all modules.
 * Allows clearing all caches at once (useful for testing).
 */

/**
 * Cache clear function type
 */
export type CacheClearFn = () => void;

/**
 * Registry of cache clear functions
 */
const cacheRegistry = new Map<string, CacheClearFn>();

/**
 * Register a cache clear function
 *
 * @param name - Unique name for this cache (for debugging/identification)
 * @param clearFn - Function that clears the cache
 */
export function registerCache(name: string, clearFn: CacheClearFn): void {
  cacheRegistry.set(name, clearFn);
}

/**
 * Unregister a cache clear function
 *
 * @param name - Name of the cache to unregister
 */
export function unregisterCache(name: string): void {
  cacheRegistry.delete(name);
}

/**
 * Clear all registered caches
 *
 * Useful for testing to ensure a clean state between tests.
 */
export function clearAllCaches(): void {
  for (const clearFn of cacheRegistry.values()) {
    clearFn();
  }
}

/**
 * Get names of all registered caches
 *
 * @returns Array of cache names
 */
export function getRegisteredCaches(): string[] {
  return Array.from(cacheRegistry.keys());
}

/**
 * Clear a specific cache by name
 *
 * @param name - Name of the cache to clear
 * @returns True if cache was found and cleared
 */
export function clearCache(name: string): boolean {
  const clearFn = cacheRegistry.get(name);
  if (clearFn) {
    clearFn();
    return true;
  }
  return false;
}
