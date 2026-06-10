import VectorStoreBase from '#app/vector-store/VectorStoreBase.js';
import AiAgent from "./llm/AiAgent.js";
import { StdClass } from "./types.js";
import LlmServiceInterface from "./llm/LlmServiceInterface.js";

export default class Services {
  private static processEnv: StdClass;
  private static llmServiceInstance: LlmServiceInterface;
  private static aiAgentInstance: AiAgent;
  private static vectorStoreInstance: VectorStoreBase;

  public static boot(
    processEnv: StdClass,
    llmService: LlmServiceInterface,
    aiAgent: AiAgent,
    vectorStore: VectorStoreBase
  ) {
    Services.processEnv = processEnv;
    Services.llmServiceInstance = llmService;
    Services.aiAgentInstance = aiAgent;
    Services.vectorStoreInstance = vectorStore;
  }

  public static llmService(): LlmServiceInterface {
    return Services.llmServiceInstance;
  }

  public static vectorStore(): VectorStoreBase {
    return Services.vectorStoreInstance;
  }

  public static aiAgent(): AiAgent {
    return Services.aiAgentInstance;
  }

  public static env(key: string | null = null, defaultValue: unknown = undefined) {
    if (key && typeof Services.processEnv[key] !== undefined) {
      return Services.processEnv[key];
    }

    return defaultValue;
  }

}