import { ENV } from "@config";
import pc from "picocolors";

type LogLevel = "debug" | "info" | "warn" | "error";

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const LEVEL_COLORS: Record<LogLevel, (s: string) => string> = {
  debug: pc.dim,
  info: pc.blue,
  warn: pc.yellow,
  error: pc.red,
};

function isValidLogLevel(level: string): level is LogLevel {
  return level in LOG_LEVELS;
}

function shouldLog(level: LogLevel): boolean {
  const configLevel = ENV.logLevel;
  const currentLevel = isValidLogLevel(configLevel)
    ? LOG_LEVELS[configLevel]
    : LOG_LEVELS.info;
  return LOG_LEVELS[level] >= currentLevel;
}

function formatMessage(level: LogLevel, message: string): string {
  const timestamp = pc.dim(new Date().toISOString());
  const levelTag = LEVEL_COLORS[level](level.toUpperCase().padEnd(5));
  return `${timestamp} ${levelTag} ${message}`;
}

export const logger = {
  debug(message: string, ...args: unknown[]): void {
    if (shouldLog("debug")) {
      console.error(formatMessage("debug", message), ...args);
    }
  },

  info(message: string, ...args: unknown[]): void {
    if (shouldLog("info")) {
      console.error(formatMessage("info", message), ...args);
    }
  },

  warn(message: string, ...args: unknown[]): void {
    if (shouldLog("warn")) {
      console.warn(formatMessage("warn", message), ...args);
    }
  },

  error(message: string, ...args: unknown[]): void {
    if (shouldLog("error")) {
      console.error(formatMessage("error", message), ...args);
    }
  },

  success(message: string, ...args: unknown[]): void {
    console.error(pc.green("✓ ") + message, ...args);
  },
};
