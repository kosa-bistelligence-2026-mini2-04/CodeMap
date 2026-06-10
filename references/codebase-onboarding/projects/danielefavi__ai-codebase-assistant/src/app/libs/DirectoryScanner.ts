import fs from 'fs/promises';
import path from 'path';
import type { Dirent, Stats } from 'fs';

/**
 * Scans a directory recursively for files with specified extensions.
 */
export default class DirectoryScanner {
  private readonly startPath: string;
  private readonly extensions: string[];
  private foundFiles: string[];

  /**
   * Creates an instance of DirectoryScanner.
   * 
   * @param startPath - The absolute or relative path to the root folder to scan. Will be resolved to an absolute path.
   * @param extensions - An array of file extensions (strings) to look for (e.g., ['.txt', '.md']).
   */
  constructor(startPath: string, extensions: string[]) {
    this.startPath = path.resolve(startPath);

    // Normalize extensions: ensure they start with '.', are lowercase, and filter out any invalid entries
    this.extensions = extensions
      .map(ext => (ext && typeof ext === 'string' ? (ext.startsWith('.') ? ext : `.${ext}`).toLowerCase() : null))
      .filter((ext): ext is string => ext !== null); // Filter out nulls and assert remaining are strings

    this.foundFiles = [];
  }

  /**
   * Initiates the recursive scan process. Resets previously found files.
   * 
   * @returns {Promise<string[]>} A promise resolving with an array of absolute file paths matching the extensions.
   * @throws {Error} If the start path does not exist or is not a directory.
   */
  async scan(): Promise<string[]> {
    try {
      // Verify the start path exists and is a directory
      const stats: Stats = await fs.stat(this.startPath);
      if (!stats.isDirectory()) {
        throw new Error(`The specified start path is not a directory: ${this.startPath}`);
      }
    } catch (err: unknown) {
      // Handle specific 'file not found' error
      if (err instanceof Error && 'code' in err && err.code === 'ENOENT') {
        throw new Error(`The specified start path does not exist: ${this.startPath}`);
      }
      // Re-throw other stat errors (e.g., permissions) with context
      const message = err instanceof Error ? err.message : String(err);
      console.error(`Error accessing start path ${this.startPath}: ${message}`);
      throw new Error(`Error accessing start path ${this.startPath}: ${message}`, { cause: err instanceof Error ? err : undefined });
    }

    this.foundFiles = [];
    await this._scanDirectory(this.startPath); // Start the recursive scan
    return this.foundFiles;
  }

  /**
   * Recursively scans a directory (private helper method).
   * 
   * @param {string} currentPath - The absolute directory path currently being scanned.
   * @private
   */
  private async _scanDirectory(currentPath: string): Promise<void> {
    let entries: Dirent[];
    try {
      // Read directory contents, getting Dirent objects for type info (more efficient than stat-ing each)
      entries = await fs.readdir(currentPath, { withFileTypes: true });
    } catch (err: unknown) {
      // Log errors like permission denied but allow the scan to continue elsewhere
      const message = err instanceof Error ? err.message : String(err);
      console.warn(`Could not read directory ${currentPath}: ${message}. Skipping.`);
      return;
    }

    // Process each entry concurrently (optional optimization)
    // await Promise.all(entries.map(async (entry) => { ... }));
    // Or sequentially for simpler logic:
    for (const entry of entries) {
      const fullPath = path.join(currentPath, entry.name);

      try {
        if (entry.isDirectory()) {
          await this._scanDirectory(fullPath);
        } else if (entry.isFile()) {
          this._checkAndAddFile(fullPath);
        }
        // Implicitly ignore symlinks, block devices, etc.
        // To follow symlinks, check entry.isSymbolicLink() and then fs.stat(fullPath)
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        console.warn(`Error processing entry ${fullPath}: ${message}. Skipping entry.`);
      }
    }
  }

  /**
   * Checks if a file's extension matches the allowed list and adds its path if it does (private helper method).
   * 
   * @param {string} filePath - The full, absolute path to the file.
   * @private
   */
  private _checkAndAddFile(filePath: string): void {
    const fileExtension = path.extname(filePath).toLowerCase();
    if (this.extensions.includes(fileExtension)) {
      this.foundFiles.push(filePath);
    }
  }

  /**
   * Reads the content of a specified file asynchronously (static utility method).
   * 
   * @param {string} filePath - The absolute or relative path to the file.
   * @param {BufferEncoding} [encoding='utf8'] - The file encoding (e.g., 'utf8', 'base64'). Defaults to 'utf8'.
   * @returns {Promise<string>} A promise that resolves with the file content as a string.
   * @throws {Error} If the file path is invalid or the file cannot be read.
   */
  static async readFileContent(filePath: string, encoding: BufferEncoding = 'utf8'): Promise<string> {
    if (!filePath || typeof filePath !== 'string') {
      throw new Error('readFileContent: filePath parameter must be a non-empty string.');
    }

    const absolutePath = path.resolve(filePath);

    try {
      const content: string = await fs.readFile(absolutePath, { encoding: encoding });
      return content;
    } catch (err: unknown) {
      const baseMessage = `Error reading file ${absolutePath}`;
      const specificMessage = err instanceof Error ? err.message : String(err);

      const errorMessage = `${baseMessage}: ${specificMessage}`;
      console.error(errorMessage);

      throw new Error(errorMessage, { cause: err instanceof Error ? err : undefined });
    }
  }
}