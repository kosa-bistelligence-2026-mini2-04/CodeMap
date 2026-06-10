import path from 'path'; // Import path for resolving folder paths
import DirectoryScanner from '#app/libs/DirectoryScanner.js';
import { calculateSHA256, extToLang } from '#app/libs/helpers.js';
import DocumentRepo from '#app/repositories/DocumentRepo.js';
import Document from '#app/models/Document.js';

interface ParentFileData {
  sha256: string;
  filename: string;
  content: string;
  parentSha256: null;
  metadata: Record<PropertyKey, unknown>;
}

type DocumentOpsData = Record<string, number>;


export default class MasterOperation {
  private readonly foldersToScan: string[];
  private readonly fileExtensionList: string[];

  /**
   * Creates an instance of MasterOperation.
   * 
   * @param foldersToScan - Array of folder paths to scan (relative or absolute).
   * @param fileExtensionList - Array of file extensions without leading dot (e.g., ['js', 'ts', 'md']).
   */
  constructor(
    foldersToScan: string[],
    fileExtensionList: string[]
  ) {
    this.foldersToScan = foldersToScan.map(folder => path.resolve(folder)); // Ensure absolute paths
    this.fileExtensionList = fileExtensionList.map(ext => ext.toLowerCase().replace(/^\./, '')); // Ensure no dot, lowercase
  }

  /**
   * Scans configured folders, compares files with DB, and creates initial parent Document records.
   * Initializes the 'operations' field for each created document.
   * 
   * @param operations - An array of operation names (strings) to initialize status for.
   * @returns A promise resolving to an array of the newly created Document instances.
   */
  async loadDbMasterData(operations: string[]): Promise<Document[]> {
    // this.validateOperations(operations);

    const parentFilesData: ParentFileData[] = await this.getParentsFileData();

    const initialOpsStatus: DocumentOpsData = operations.reduce((acc, key) => {
      acc[key] = 0; 
      return acc;
    }, {} as DocumentOpsData);

    const createdOrUpdatedDocs: Document[] = [];

    for (const fileData of parentFilesData) {
      createdOrUpdatedDocs.push(await DocumentRepo.create({
        ...fileData,
        operations: initialOpsStatus,
        status: Document.DOCUMENT_STATUS.TO_PROCESS
      }));
    }

    console.log(`Master data load finished. ${createdOrUpdatedDocs.length} entries created/updated.`);
    return createdOrUpdatedDocs;
  }

  /**
   * Gathers data for all potential parent files across all configured folders and extensions.
   * 
   * @private
   * @returns {Promise<ParentFileData[]>} A list of data objects for parent files.
   */
  private async getParentsFileData(): Promise<ParentFileData[]> {
    const allParentFiles: ParentFileData[] = [];

    for (const ext of this.fileExtensionList) {
      const lang = extToLang(`.${ext}`);

      for (const folderToScan of this.foldersToScan) {
        const filesInData = await this.getParentsFileDataByExtension(folderToScan, ext, lang);

        if (filesInData.length > 0) {
          allParentFiles.push(...filesInData);
        }
      }
    }
    return allParentFiles;
  }

  /**
   * Scans a specific folder for a given extension, compares with DB, and returns data for new/updated parent content documents.
   * 
   * @private
   * @param {string} folderToScan - Absolute path to the folder.
   * @param {string} ext - File extension without dot.
   * @param {(string | null)} lang - Associated language name.
   * @returns {Promise<ParentFileData[]>} List of data objects for parent files found in this folder/extension.
   */
  private async getParentsFileDataByExtension(folderToScan: string, ext: string, lang: string | null): Promise<ParentFileData[]> {
    const scanner = new DirectoryScanner(folderToScan, [`.${ext}`]);
    const matchingFiles: string[] = await scanner.scan(); // Gets absolute paths

    const filesToProcess: ParentFileData[] = [];

    for (const filePath of matchingFiles) {
      const content: string = await DirectoryScanner.readFileContent(filePath);

      const sha256: string = calculateSHA256(content);

      const fileContents: Document[] = await DocumentRepo.getMasterDocument(filePath, sha256);

      // file unchanged
      if (fileContents.length) continue;
      
      // file changed or not present
      await Document.destroy({ where: { filename: filePath } });

      filesToProcess.push({
        sha256: sha256,
        filename: filePath,
        content: content,
        parentSha256: null, // this is a parent content
        metadata: {
          language: lang,
          fileExtension: ext
        }
      });
    } // end loop for matchingFiles

    return filesToProcess;
  }

}