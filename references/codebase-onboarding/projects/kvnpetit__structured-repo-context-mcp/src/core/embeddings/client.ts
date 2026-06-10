/**
 * Ollama client for generating embeddings
 * Uses the official ollama library
 */

import { Ollama } from "ollama";
import type { EmbeddingConfig } from "@core/embeddings/types";

export class OllamaClient {
  private readonly client: Ollama;
  private readonly model: string;

  constructor(
    config: Pick<EmbeddingConfig, "ollamaBaseUrl" | "embeddingModel">,
  ) {
    this.client = new Ollama({ host: config.ollamaBaseUrl });
    this.model = config.embeddingModel;
  }

  /**
   * Generate embeddings for a single text
   */
  async embed(text: string): Promise<number[]> {
    const response = await this.client.embed({
      model: this.model,
      input: text,
    });

    const result = response.embeddings[0];
    if (!result) {
      throw new Error("No embedding returned from Ollama");
    }
    return result;
  }

  /**
   * Generate embeddings for multiple texts in a single request
   */
  async embedBatch(texts: string[]): Promise<number[][]> {
    const response = await this.client.embed({
      model: this.model,
      input: texts,
    });

    return response.embeddings;
  }

  /**
   * Check if Ollama is reachable and the model is available
   */
  async healthCheck(): Promise<{ ok: boolean; error?: string }> {
    try {
      const response = await this.client.list();
      const models = response.models;
      const modelExists = models.some(
        (m) => m.name === this.model || m.name.startsWith(`${this.model}:`),
      );

      if (!modelExists) {
        return {
          ok: false,
          error: `Model "${this.model}" not found. Run: ollama pull ${this.model}`,
        };
      }

      return { ok: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return { ok: false, error: `Cannot connect to Ollama: ${message}` };
    }
  }
}

/**
 * Create a new Ollama client with default config
 */
export function createOllamaClient(
  config: Pick<EmbeddingConfig, "ollamaBaseUrl" | "embeddingModel">,
): OllamaClient {
  return new OllamaClient(config);
}
