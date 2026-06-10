import { createHash } from 'crypto';
import { EXT_TO_LANG } from '../settings.js';

/**
 * Calculates the SHA-256 hash of a string asynchronously.
 *
 * @param {string} inputString The string to hash.
 * @returns {string} A promise that resolves with the SHA-256 hash as a hexadecimal string.
 */
export function calculateSHA256(inputString: string): string {
  const hash = createHash('sha256');
  hash.update(inputString);
  return hash.digest('hex');
}

export function extToLang(ext: string): string | null {
  return EXT_TO_LANG[ext] ?? null;
}

export function isACodingLanguage(lang: string): boolean {
  return [
    'html',
    'cpp',
    'go',
    'java',
    'javascript',
    'php',
    'proto',
    'python',
    'rst',
    'ruby',
    'rust',
    'scala',
    'swift',
    'latex',
    'sol'
  ].includes(lang);
}

export function errorWithCause(message: string, error: any): Error {
  return new Error('Failed to fetch data from Ollama', {
    cause: {
      message: error.message,
      stack: error.stack,
      ...(error.cause && { cause: String(error.cause) }),
    }
  });
}