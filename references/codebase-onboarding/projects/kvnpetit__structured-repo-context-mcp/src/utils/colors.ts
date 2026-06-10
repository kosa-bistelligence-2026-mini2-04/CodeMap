import pc from "picocolors";

/**
 * Color utilities for CLI output
 */
export const colors = {
  // Status colors
  success: pc.green,
  error: pc.red,
  warn: pc.yellow,
  info: pc.blue,

  // UI elements
  dim: pc.dim,
  bold: pc.bold,
  cyan: pc.cyan,
  magenta: pc.magenta,

  // Composite helpers
  successBold: (text: string): string => pc.bold(pc.green(text)),
  errorBold: (text: string): string => pc.bold(pc.red(text)),
  infoBold: (text: string): string => pc.bold(pc.blue(text)),

  // Format messages with icons
  formatSuccess: (msg: string): string => `${pc.green("✓")} ${msg}`,
  formatError: (msg: string): string => `${pc.red("✗")} ${msg}`,
  formatInfo: (msg: string): string => `${pc.blue("ℹ")} ${msg}`,
  formatWarn: (msg: string): string => `${pc.yellow("⚠")} ${msg}`,

  // Format for CLI output
  formatCommand: (cmd: string): string => pc.cyan(cmd),
  formatValue: (val: string): string => pc.magenta(val),
  formatPath: (path: string): string => pc.dim(path),
};
