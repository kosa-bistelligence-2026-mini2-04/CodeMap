import { StdClass } from '#app/libs/types.js';
import Document from '#app/models/Document.js';
import {
  Sequelize, // Make sure Sequelize itself is imported
  InferAttributes,
  CreationAttributes,
  WhereOptions,
  Op
} from 'sequelize';

/**
 * Repository class encapsulating database access logic for the Document model.
 */
export default class DocumentRepo {

  static async create(data: CreationAttributes<Document>) {
    return await Document.create(data);
  }

  /**
   * Retrieves the parent (root) document associated with a specific filename.
   * Root documents are identified by having `parentSha256` set to `null`.
   * 
   * @param   {string}              filename  [filename description]
   * @param   {string<Document>[]}   sha256    [sha256 description]
   * @return  {Promise<Document>[]}            [return description]
   */
  static async getMasterDocument(filename: string, sha256: string): Promise<Document[]> {
    if (filename.trim() === '') {
      throw new Error('Invalid filename provided to getContentsFromFile.');
    }

    return await Document.findAll({
      where: {
        filename: filename,
        sha256,
        parentSha256: null
      }
    });
  }

  /**
   * Checks if a Document exists in the database matching the given filename and sha256 hash.
   * Performs an optimized query by only selecting the 'id'.
   *
   * @param {string} filename - The filename to check for.
   * @param {string} sha256 - The sha256 hash to check for.
   * @returns {Promise<boolean>} A promise that resolves to true if a matching document exists, false otherwise.
   * @throws {Error} Throws an error if input parameters are invalid. Database query errors might also propagate.
   */
  static async documentExists(filename: string, sha256: string): Promise<boolean> {
    if (filename.trim() === '') {
      throw new Error('Invalid filename provided to documentExists.');
    }
    if (sha256.trim() === '') {
      throw new Error('Invalid sha256 provided to documentExists.');
    }

    const existingDoc: Document | null = await Document.findOne({
      where: {
        filename: filename,
        sha256: sha256
      },
      attributes: ['id'] // only fetch the ID column
    });

    return existingDoc !== null;
  }

  /**
   * Get a random record from the documents table and return its related Content model.
   *
   * @param {WhereOptions<InferAttributes<Document>>} [where={}]
   * @returns {Promise<Document | null>}
   */
  static async getRandomDocument(where: WhereOptions<InferAttributes<Document>> = {}): Promise<Document | null> {
    try {
      return await Document.findOne({
        where: where,
        order: [
          Sequelize.fn('RAND')
        ]
      });
    } catch (error) {
      console.error("Error fetching random document:", error);
      return null;
    }
  }

  static async getRandomToProcess(includeFailed: boolean = false, maxErrors: number = 3): Promise<Document | null> {
    const where: StdClass = {};
    const statusList: string[] = [ Document.DOCUMENT_STATUS.TO_PROCESS ];

    if (includeFailed) {
      statusList.push(Document.DOCUMENT_STATUS.ERROR);
      where.errorCount = { [Op.lt]: maxErrors };
    }

    where.status = {
      [Op.in]: statusList
    };

    try {
      return await Document.findOne({
        where,
        order: [
          Sequelize.fn('RAND')
        ]
      });
    } catch (error) {
      console.error("Error fetching random document:", error);
      return null;
    }
  }

}