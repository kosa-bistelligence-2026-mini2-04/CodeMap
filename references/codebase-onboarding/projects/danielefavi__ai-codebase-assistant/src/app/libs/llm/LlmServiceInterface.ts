import { BaseLLM } from "@langchain/core/language_models/llms";
import { Embeddings } from '@langchain/core/embeddings';
import { StdClass } from "../types.js";

export default interface LlmServiceInterface {
  init(): void;

  getLlm(model: string): BaseLLM;
  getDefaultLlm(): BaseLLM;
  getEmbeddingsLlm(model: string): Embeddings;
  getDefaultEmbeddingsLlm(): Embeddings;

  getModels(): Promise<StdClass[]>;
  modelExists(model: string): Promise<boolean>;
}