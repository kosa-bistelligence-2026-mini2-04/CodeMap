import Document from "#app/models/Document.js";
import { OperationResult, StdClass } from "../types.js";
import AbstractOperation from "./AbstractOperation.js";
import Services from "../Services.js";

export default class StoreInVectorDbOperation extends AbstractOperation {
  public static readonly operationName: string  = 'storeInVectorDb';

  async performOperation(record: Document, extra: StdClass = {}): Promise<OperationResult> {
    const metadata = record.metadata as Record<PropertyKey, unknown>;

    metadata.sha256 = record.sha256;
    metadata.filename = record.filename;
    metadata.parentSha256 = record.parentSha256;

    await Services.vectorStore().getClient().delete({
      filter: { sha256: record.sha256 }
    });

    try {
      const id = await Services.vectorStore().addDocument({
        pageContent: record.content as string,
        metadata
      });

      if (id) {
        record.vectorStoreId = id;
        record.save();
      }

      return this.successResponse('Data store in vector DB: ' + id);  
    } catch (error) {
      console.error('Failed to add document in vector store', error, {
        record, metadata
      });

      throw error;
    }
  }
}