import { BaseLLM } from "@langchain/core/language_models/llms";
import { Embeddings } from '@langchain/core/embeddings';
import LlmServiceInterface from "./LlmServiceInterface.js";
import { errorWithCause } from "../helpers.js";
import { StdClass } from "../types.js";
import { Ollama, OllamaEmbeddings } from "@langchain/ollama";

type LlmSetting = {
  driver: string,
  host: string,
  port: string
  defaultLlm: string
  defaultEmbedding: string
}

export default class OllamaLlmService implements LlmServiceInterface {
  private llmSetting: LlmSetting;

  private llmInstances: Record<string, BaseLLM> = {};
  private embeddings: Record<string, Embeddings> = {};


  constructor(
    llmSetting: LlmSetting
  ) {
    this.llmSetting = llmSetting;
  }

  async init() {
    if (!await this.modelExists(this.llmSetting.defaultLlm)) {
      throw new Error(`The LLM "${this.llmSetting.defaultLlm}" is not valid.`);
    }
    if (!await this.modelExists(this.llmSetting.defaultEmbedding)) {
      throw new Error(`The LLM "${this.llmSetting.defaultEmbedding}" is not valid.`);
    }
  }

  getDefaultLlm(): BaseLLM {
    return this.getLlm(this.llmSetting.defaultLlm);
  }

  getLlm(model: string): BaseLLM {
    let llm = this.llmInstances[model] ?? null;

    if (llm) {
      return llm;
    }

    this.llmInstances[model] = new Ollama({
      model,
      baseUrl: `http://${this.llmSetting.host}:${this.llmSetting.port}`
    });

    return this.llmInstances[model];
  }

  getDefaultEmbeddingsLlm(): Embeddings {
    return this.getEmbeddingsLlm(this.llmSetting.defaultEmbedding);
  }

  getEmbeddingsLlm(model: string): Embeddings {
    let emb = this.embeddings[model] ?? null;

    if (emb) {
      return emb;
    }
  
    this.embeddings[model] = new OllamaEmbeddings({
      model,
      baseUrl: `http://${this.llmSetting.host}:${this.llmSetting.port}`
    });
  
    return this.embeddings[model];
  }

  getLlmServiceUrl(partialUrl: string = ''): string {
    return `http://${this.llmSetting.host}:${this.llmSetting.port}/` + partialUrl.replace(/^\//, '');
  }

  async getModels(): Promise<StdClass[]> {
    let response = null;
    try {
      response = await fetch(this.getLlmServiceUrl('/api/tags'));
    } catch (error: any) {
      throw errorWithCause('Failed to fetch data from Ollama', error);
    }
    
    if (!response) {
      throw new Error('The given response is NULL');
    }

    if (!response.ok) {
      throw new Error(`Failed to fetch models from Ollama: ${response.statusText}`);
    }

    const data = await response.json();

    return data.models;
  }

  async modelExists(model: string): Promise<boolean> {
    const models = await this.getModels();

    return models.map(model => model.name as string).includes(model);
  }
}