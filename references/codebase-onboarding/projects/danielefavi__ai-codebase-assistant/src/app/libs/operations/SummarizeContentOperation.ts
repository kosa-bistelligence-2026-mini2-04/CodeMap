import Document from "#app/models/Document.js";
import { BaseLLM } from "@langchain/core/language_models/llms";
import { OperationResult, StdClass } from "../types.js";
import AbstractOperation from "./AbstractOperation.js";
import { calculateSHA256, isACodingLanguage } from "../helpers.js";
import DocumentRepo from "#app/repositories/DocumentRepo.js";
import Services from "../Services.js";

export default class SummarizeContentOperation extends AbstractOperation {
  public static readonly operationName: string  = 'summarizeContent';

  async performOperation(record: Document, extra: StdClass = {}): Promise<OperationResult> {
    console.log('running operation SummarizeContentOperation');

    if (!record.filename) {
      throw new Error('Filename is empty in SummarizeContentOperation');
    }

    if (!record.content || !record.content.trim().length) {
      return this.successResponse('Skipped: content is empty.');
    }

    try {
      const summary = await this.summarize(record);
      const sha256 = calculateSHA256(summary);
  
      if (await DocumentRepo.documentExists(record.filename, sha256)) {
        return this.successResponse(`The content with filename ${record.filename} and sha256 ${sha256} already exists.`);
      }
  
      await DocumentRepo.create({
        sha256,
        filename: record.filename,
        content: summary,
        parentSha256: record.sha256,
        metadata: {
          summaryOf: record.sha256,
          language: record.metadata?.language,
          fileExtensions: record.metadata?.fileExtensions,
          loc: record.metadata?.loc,
          splits: record.metadata?.splits,
        },
        operations: {
          storeInVectorDb: 0
        }
      });
      
      return this.successResponse('Summarized'); 
    } catch (error) {
      console.error(`Error occurred while summarizing record ${record.id}`, error);
      return this.errorResponse(`Error occurred while summarizing record ${record.id} `, error);
    }
  }

  async summarize(record: Document): Promise<string> {
    const agent = Services.aiAgent();
    
    let contextInfo = '';
    let codingLang: null | string = null;

    if (record.metadata?.language) {
      codingLang = record.metadata.language as string;
      contextInfo += ` - Coding language: ${codingLang}\n`;
    }

    if (record.metadata?.filemane) {
      contextInfo += ` - Coding language: ${record.metadata.filemane}\n`;
    }

    if (codingLang && isACodingLanguage(codingLang)) {
      return await agent.describeCode(record.content as string, contextInfo);
    }
    
    const summary = await agent.summarizeText(record.content as string, contextInfo);
    return summary.replace(/<think>.*?<\/think>/gs, '').trim();
  }

}