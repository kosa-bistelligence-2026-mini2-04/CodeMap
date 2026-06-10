import Document from "#app/models/Document.js";
import { RecursiveCharacterTextSplitter, SupportedTextSplitterLanguage } from "@langchain/textsplitters";
import { OperationResult, StdClass } from "../types.js";
import { EXT_TO_LANG } from "#app/settings.js";
import AbstractOperation from "./AbstractOperation.js";
import { calculateSHA256 } from "../helpers.js";
import DocumentRepo from "#app/repositories/DocumentRepo.js";

export default class ChunkContentOperation extends AbstractOperation {
  public static readonly operationName: string  = 'chunkContent';

  async performOperation(record: Document, extra: StdClass = {}): Promise<OperationResult> {
    try {
      return await this.performChunking(record, extra);
    } catch (error) {
      console.error('Error occurred on chunking operation', error);
      return this.errorResponse('Error occurred on chunking operation', error);
    }
  }

  async performChunking(record: Document, extra: StdClass = {}): Promise<OperationResult> {
    const chunkSize = extra.chunkSize as number || 2000;
    const chunkOverlap = extra.chunkOverlap as number || 200;

    const ext = record.metadata?.fileExtension ? record.metadata?.fileExtension as string : 'txt';
    const lang = this.getLanguageFromExt(ext);

    const recSplitter = this.getSplitter(lang, chunkSize, chunkOverlap);

    const splits = await recSplitter.createDocuments([record.content as string], [{
      language: lang,
      fileExtensions: ext
    }]);

    if (splits.length === 1) {
      return this.successResponse('Total split is 1. Skipping it.');
    }

    let splitCounter = 0;
    for (const split of splits) {
      splitCounter++;

      if (!record.filename) {
        continue;
      }

      const sha256 = calculateSHA256(split.pageContent);

      // if the filename/sha256 already exists with a status success, then continue
      if (await DocumentRepo.documentExists(record.filename, sha256)) {
        continue;
      }

      const splitMeta = split.metadata;

      if (splitMeta?.loc?.lines?.from && splitMeta?.loc?.lines?.to) {
        splitMeta.fromLine = splitMeta.loc.lines.from;
        splitMeta.toLine = splitMeta.loc.lines.to;
        delete splitMeta?.loc;
      }

      // store the split
      await DocumentRepo.create({
        sha256,
        filename: record.filename,
        content: split.pageContent,
        parentSha256: record.sha256,
        metadata: {
          ...splitMeta,
          splitNum: splitCounter + 1,
          splitTotal: splits.length
        },
        operations: {
          summarizeContent: 0,
          storeInVectorDb: 0
        }
      });
    }

    return this.successResponse('Chunks created');
  }

  getSplitter(lang: SupportedTextSplitterLanguage | null, chunkSize: number = 2000, chunkOverlap: number = 200) {
    if (lang) {
      return RecursiveCharacterTextSplitter.fromLanguage(lang, {
        chunkSize: chunkSize,
        chunkOverlap: chunkOverlap
      });
    }

    return new RecursiveCharacterTextSplitter({
      chunkSize: chunkSize,
      chunkOverlap: chunkOverlap
    });    
  }

  getLanguageFromExt(ext: string): SupportedTextSplitterLanguage | null {
    if (EXT_TO_LANG[ext]) {
      return EXT_TO_LANG[ext] as SupportedTextSplitterLanguage;
    }
    
    return null;
  }
}