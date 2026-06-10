/**
 * Language configuration and mapping for Tree-sitter parsers
 * Reads from centralized assets/languages.json
 */
import { loadJsonConfig, registerCache } from "@core/utils";

export interface LanguageConfig {
  name: string;
  wasm: string;
  queries: string;
  extensions: string[];
  aliases?: string[];
}

interface LanguagesConfig {
  treesitter: Record<
    string,
    {
      wasm: string;
      queries: string;
      extensions: string[];
      aliases?: string[];
    }
  >;
}

let configCache: LanguagesConfig | null = null;
let languagesCache: Record<string, LanguageConfig> | null = null;
let extensionMapCache: Record<string, LanguageConfig> | null = null;

function loadConfig(): LanguagesConfig {
  if (configCache) {
    return configCache;
  }

  configCache = loadJsonConfig<LanguagesConfig>("languages.json", {
    treesitter: {},
  });
  return configCache;
}

function buildLanguages(): Record<string, LanguageConfig> {
  if (languagesCache) {
    return languagesCache;
  }

  const config = loadConfig();
  languagesCache = {};

  for (const [name, lang] of Object.entries(config.treesitter)) {
    languagesCache[name] = {
      name,
      wasm: lang.wasm,
      queries: lang.queries,
      extensions: lang.extensions,
      aliases: lang.aliases,
    };

    // Also register aliases
    if (lang.aliases) {
      for (const alias of lang.aliases) {
        languagesCache[alias] = {
          name,
          wasm: lang.wasm,
          queries: lang.queries,
          extensions: lang.extensions,
          aliases: lang.aliases,
        };
      }
    }
  }

  return languagesCache;
}

function buildExtensionMap(): Record<string, LanguageConfig> {
  if (extensionMapCache) {
    return extensionMapCache;
  }

  const languages = buildLanguages();
  extensionMapCache = {};

  for (const config of Object.values(languages)) {
    for (const ext of config.extensions) {
      extensionMapCache[ext] = config;
    }
  }

  return extensionMapCache;
}

/** Get all Tree-sitter supported languages */
export function getLanguages(): Record<string, LanguageConfig> {
  return buildLanguages();
}

/** Get language configuration from file extension */
export function getLanguageFromExtension(
  extension: string,
): LanguageConfig | undefined {
  const ext = extension.startsWith(".") ? extension : `.${extension}`;
  return buildExtensionMap()[ext.toLowerCase()];
}

/** Get language configuration from file path */
export function getLanguageFromPath(
  filePath: string,
): LanguageConfig | undefined {
  const ext = filePath.slice(filePath.lastIndexOf(".")).toLowerCase();
  return buildExtensionMap()[ext];
}

/** Get language configuration by name */
export function getLanguageByName(name: string): LanguageConfig | undefined {
  return buildLanguages()[name.toLowerCase()];
}

/** Check if a language is supported by Tree-sitter */
export function isLanguageSupported(language: string): boolean {
  return language.toLowerCase() in buildLanguages();
}

/** Get all supported language names */
export function getSupportedLanguages(): string[] {
  return Object.keys(loadConfig().treesitter);
}

/** Get all supported file extensions */
export function getSupportedExtensions(): string[] {
  return Object.keys(buildExtensionMap());
}

/** Clear caches (for testing) */
export function clearLanguageCache(): void {
  configCache = null;
  languagesCache = null;
  extensionMapCache = null;
}

// Legacy exports for backward compatibility
export const LANGUAGES = buildLanguages();
export const EXTENSION_MAP = buildExtensionMap();

// Register cache for centralized clearing
registerCache("languages:config", clearLanguageCache);
