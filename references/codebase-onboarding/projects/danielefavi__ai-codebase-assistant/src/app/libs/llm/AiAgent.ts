import { PromptTemplate } from "@langchain/core/prompts";
import { PROMPT_FOR_SUMMARIZING_CODE, PROMPT_FOR_SUMMARIZING_TEXT, PROMPT_FOR_REFINING_PROMPT, PROMPT_USER_QUERY_AND_DATA_CONTEXT } from "#app/settings.js";
import { RagOptions, StdClass } from "../types.js";
import Services from "../Services.js";
import LlmServiceInterface from "./LlmServiceInterface.js";
import { BaseLLM } from "@langchain/core/language_models/llms";
import { DocumentInterface } from "@langchain/core/documents";
import Document from "#app/models/Document.js";


export default class AiAgent {
  private llmService: LlmServiceInterface;

  constructor(llmService: LlmServiceInterface) {
    this.llmService = llmService;
  }

  async summarizeText(inputText: string, contextInfo: string = ''): Promise<string> {
    return await this.summarize(PROMPT_FOR_SUMMARIZING_TEXT, inputText, contextInfo);
  }

  async describeCode(inputText: string, contextInfo: string = ''): Promise<string> {
    return await this.summarize(PROMPT_FOR_SUMMARIZING_CODE, inputText, contextInfo);
  }

  async summarize(template: string, inputText: string, contextInfo: string = ''): Promise<string> {
    const prompt = new PromptTemplate({
      inputVariables: ['contextInfo', 'inputText'],
      template,
    });

    const chain = prompt.pipe(this.llmService.getDefaultLlm());

    if (contextInfo.trim().length) {
      contextInfo = `Context Information:\n${contextInfo}`;
    }

    return await chain.invoke({
      contextInfo,
      inputText
    });
  }

  async refinePrompt(userQuestion: string, model: BaseLLM): Promise<string> {

    const promptTemplate = PromptTemplate.fromTemplate(
      PROMPT_FOR_REFINING_PROMPT
    );

    const chain = promptTemplate.pipe(model);

    return await chain.invoke({ userQuestion });
  }

  async rag(userQuery: string, options: RagOptions) {
    // 1) refine user prompt
    let refinedUserQuery = await this.refineUserQuery(userQuery, options);

    // 2) query vector store
    const vectorStore = Services.vectorStore().getClient();
    const searchResult = await vectorStore.similaritySearch(refinedUserQuery, options.similaritySearchResults);

    // 3) foreach result retrieve the related piece
    let contextData = await this.getChunksForFinalQuestionAsText(searchResult);

    // 4) combine the user query and the data from the vector store in a prompt and send it to the LLM
    const model = Services.llmService().getDefaultLlm();
    const finalAnswer = await this.getFinalAnswer(userQuery,contextData, model);

    return {
      userQuery,
      refinedUserQuery,
      searchResult,
      contextData,
      finalAnswer
    }
  }

  async getFinalAnswer(userQuery: string, contextData: string, model: BaseLLM): Promise<string> {

    const promptTemplate = PromptTemplate.fromTemplate(
      PROMPT_USER_QUERY_AND_DATA_CONTEXT
    );

    const chain = promptTemplate.pipe(model);

    return await chain.invoke({ userQuery, contextData });
  }

  async getChunksForFinalQuestionAsText(
    searchResult: DocumentInterface<Record<string, any>>[]
  ): Promise<string> {
    const processed: string[] = [];
    let text = '';

    for (let i = 0; i < searchResult.length; i++) {
      const sha256 = searchResult[i].metadata.sha256;
      const summaryOf = searchResult[i].metadata.summaryOf ?? null;
      
      if (processed.includes(sha256) || processed.includes(summaryOf)) {
        continue;
      }

      if (summaryOf) {
        text += searchResult[i].pageContent;
        const doc = await this.getDocumentBySha(summaryOf);
        if (doc) {
          text += '\n\n' + doc.content;
          processed.push(doc.sha256);
        }
      } else {
        const doc = await this.getDocumentBySummaryOf(sha256);
        if (doc) {
          text += doc.content + '\n\n';
          processed.push(doc.sha256);
        }
        text += searchResult[i].pageContent;
      }

      processed.push(sha256);
    }
    
    return text;
  }

  /**
   * @TODO: currently is taking the document from the SQL DB, it should come from the vector store instead
   *
   * @param   {string<Document>}   sha256
   * @return  {Promise<Document | null>}
   */
  async getDocumentBySha(sha256: string): Promise<Document | null> {
    return await Document.findOne({
      where: {
        sha256
      }
    });
  }

  /**
   * @TODO: currently is taking the document from the SQL DB, it should come from the vector store instead
   *
   * @param   {string<Document>}   sha256
   * @return  {Promise<Document | null>}
   */
  async getDocumentBySummaryOf(summaryOfSha256: string): Promise<Document | null> {
    return await Document.findOne({
      where: {
        'metadata.summaryOf': summaryOfSha256
      }
    });
  }

  async refineUserQuery(userQuestion: string, options: RagOptions): Promise<string> {
    let refinedQuestion = userQuestion;

    if (options.refineUserPrompt) {
      const modelStr = options.model || Services.env('LLM_MODEL_REFINE_QUERY');

      if (typeof modelStr !== 'string') {
        throw new Error('The model given to RAG function is not valid.');
      }

      refinedQuestion = await this.refinePrompt(userQuestion, this.llmService.getLlm(modelStr));
      refinedQuestion = userQuestion.replace(/<think>[\s\S]*?<\/think>\s*/, '').trim();
    }

    return refinedQuestion;
  }

}