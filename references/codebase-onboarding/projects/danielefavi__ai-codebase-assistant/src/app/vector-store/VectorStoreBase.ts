import { VectorStore } from "@langchain/core/vectorstores";
import { EmbeddingsInterface } from "@langchain/core/embeddings";
import type { Document as VectorDbDocument } from "@langchain/core/documents";
import { VectorStoreEntry } from "#app/libs/types.js";
import { Collection } from "chromadb";

export default abstract class VectorStoreBase {
  protected readonly embeddingsModel: EmbeddingsInterface;
  protected readonly client: VectorStore;

  abstract deleteEverything(): Promise<void>;
  abstract getLatestEntries(limit: number): Promise<VectorStoreEntry[]>;
  abstract getDefaultCollection(): Promise<Collection>;

  constructor(embeddingsModel: EmbeddingsInterface, client: VectorStore) {
    this.embeddingsModel = embeddingsModel;
    this.client = client;
  }

  getClient(): VectorStore {
    return this.client;
  }

  getEmbeddingsModel(): EmbeddingsInterface {
    return this.embeddingsModel;
  }

  async addDocument(document: VectorDbDocument): Promise<string | null> {
    const ids = await this.client.addDocuments([document]);

    return Array.isArray(ids) ? ids[0] as string : null;
  }

  async addDocuments(documents: VectorDbDocument[]): Promise<string[] | null> {
    const ids = await this.client.addDocuments(documents);

    return Array.isArray(ids) ? ids : null;
  }

  async deleteById(id: string | string[]): Promise<void> {
    if (!Array.isArray(id)) {
      id = [ id ];
    }

    await this.client.delete({ ids: id });
  }

}