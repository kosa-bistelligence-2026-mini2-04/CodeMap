import { EmbeddingsInterface } from "@langchain/core/embeddings";
import VectorStoreBase from "./VectorStoreBase.js";
import { Chroma } from "@langchain/community/vectorstores/chroma";
import { ChromaClient, Collection, IncludeEnum } from 'chromadb';
import { StdClass, VectorStoreEntry } from "#app/libs/types.js";

export default class ChromaVectorStore extends VectorStoreBase {
  private directChromaClient: ChromaClient | null = null;
  private chromaHost: string;
  private collectionName: string;

  constructor(embeddingsModel: EmbeddingsInterface, chromaHost:string, collectionName: string) {
    const vectorStore = new Chroma(embeddingsModel, {
      collectionName,
      url: chromaHost,
      collectionMetadata: {
        "hnsw:space": "cosine", // https://docs.trychroma.com/usage-guide#changing-the-distance-function
      }
    });

    super(embeddingsModel, vectorStore);

    this.chromaHost = chromaHost;
    this.collectionName = collectionName;
  }

  getDirectChromaClient(): ChromaClient {
    if (this.directChromaClient) {
      return this.directChromaClient;
    }

    this.directChromaClient = new ChromaClient({ path: this.chromaHost });

    return this.directChromaClient;
  }

  async getDefaultCollection(): Promise<Collection> {
    return await this.getDirectChromaClient()
      .getCollection({ name: this.collectionName });
  }

  async getLatestEntries(limit: number = 50): Promise<VectorStoreEntry[]> {
    const client = this.getDirectChromaClient();

    const collection = await client.getCollection({ name: this.collectionName });

    const results = await collection.get({
      limit,
      include: [IncludeEnum.Metadatas, IncludeEnum.Documents]
    });

    const sortedEntries = results.metadatas
      .map((metadata, index) => ({
        id: results.ids[index],
        metadata: metadata,
        document: results.documents ? results.documents[index] : null,
        // embedding: results.embeddings ? results.embeddings[index] : null
      }))

    return sortedEntries;
  }

  async deleteEverything(): Promise<void> {
    const client = this.getDirectChromaClient();

    const collection: Collection = await client.getOrCreateCollection({ name: this.collectionName });

    console.log(`Attempting to delete collection: "${this.collectionName}"`);

    await client.deleteCollection({ name: this.collectionName });
    console.log(`Collection "${this.collectionName}" deleted successfully.`);

    const newCollection: Collection = await client.getOrCreateCollection({ name: this.collectionName });
    console.log(`Collection "${this.collectionName}" re-created successfully and is now empty.`);
  }

}