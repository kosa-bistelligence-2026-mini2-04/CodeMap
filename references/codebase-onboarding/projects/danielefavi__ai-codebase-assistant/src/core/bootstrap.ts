import dotenv from 'dotenv';
import { sequelize, testDbConnection } from './database.js';
import OllamaLlmService from '#app/libs/llm/OllamaLlmService.js';
import Services from '#app/libs/Services.js';
import AiAgent from '#app/libs/llm/AiAgent.js';
import { StdClass } from '#app/libs/types.js';
import LlmServiceInterface from '#app/libs/llm/LlmServiceInterface.js';
import VectorStoreBase from '#app/vector-store/VectorStoreBase.js';
import ChromaVectorStore from '#app/vector-store/ChromaVectorStore.js';

dotenv.config();

/**
 * Initializes the application's core components.
 * Currently, it tests the database connection and synchronizes Sequelize models.
 *
 * WARNING: Using `sequelize.sync()` in production is generally discouraged
 * as it can lead to data loss (`force: true`) or unexpected issues
 * (`alter: true`). Database migrations are the recommended approach
 * for managing schema changes in production environments.
 *
 * @returns {Promise<void>} Resolves when initialization is successful, otherwise exits the process on error.
 */
export default async function bootstrap(): Promise<void> {
  try {
    await testDbConnection();

    console.log('Synchronizing Sequelize models...');
    await sequelize.sync();
    console.log('Sequelize models synchronized successfully.');

    await initServices();
  } catch (error: unknown) {
    console.error('Critical error during application bootstrap:');
    if (error instanceof Error) {
      console.error(`   Error: ${error.message}`);
    } else {
      console.error('   An unknown error object was caught:', error);
    }
    process.exit(1);
  }
}


async function initServices() {
  let llmService: LlmServiceInterface | null  = null;
  let vectorStore: VectorStoreBase | null  = null;


  if (process.env.LLM_DRIVER === 'ollama') {
    llmService = new OllamaLlmService(
      {
        driver: process.env.LLM_DRIVER as string,
        host: process.env.LLM_HOST as string,
        port: process.env.LLM_PORT as string,
        defaultLlm: process.env.LLM_MODEL as string,
        defaultEmbedding: process.env.LLM_EMBEDDING_MODEL as string
      }
    );

    await llmService.init();
  } else {
    throw new Error('LLM_DRIVER not valid or not configured');
  }
  
  if (process.env.VECTOR_DB_DRIVER === 'chroma') {
    vectorStore = new ChromaVectorStore(
      llmService.getDefaultEmbeddingsLlm(),
      process.env.VECTOR_DB_URL as string,
      process.env.VECTOR_DB_COLLECTION_NAME as string
    );
  } else {
    throw new Error('VECTOR_DB_DRIVER not valid or not configured');
  }

  Services.boot(
    process.env as StdClass,
    llmService,
    new AiAgent(llmService),
    vectorStore
  );


  console.log('LLM service initialized.');


}