/**
 * Core utilities barrel export
 */

// Asset directory utilities
export {
  assetExists,
  clearAssetsDirCache,
  getAssetPath,
  getAssetsDir,
  loadJsonConfig,
} from "./assets";

// Cache management
export {
  clearAllCaches,
  clearCache,
  getRegisteredCaches,
  registerCache,
  unregisterCache,
  type CacheClearFn,
} from "./cache";

// TSConfig utilities
export {
  clearPathAliasCache,
  readPathAliases,
  readPathAliasesCached,
  type PathAliases,
} from "./tsconfig";
