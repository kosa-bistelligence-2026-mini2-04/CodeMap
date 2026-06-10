import { Request, Response } from 'express';
import BaseController from './BaseController.js';
import { BaseLLM } from '@langchain/core/language_models/llms';
import Services from '#app/libs/Services.js';
import { RagOptions } from '#app/libs/types.js';

export default class AgentController extends BaseController {

  async genericQuestionStream(req: Request, res: Response) {
    const data = req.body;

    this.validate(data, {
      query: 'required'
    });

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();

    const llm = Services.llmService().getDefaultLlm();
    const stream = await llm.stream(data.query);

    for await (const chunk of stream) {
      const responsePayload = { token: chunk };
      res.write(`data: ${JSON.stringify(responsePayload)}\n\n`);
    }

    res.write('data: [DONE]\n\n');
    res.end();

  }

  async genericQuestion(req: Request, res: Response): Promise<Response> {
    const data = req.body;

    this.validate(data, {
      query: 'required',
    });

    let llm: BaseLLM | null = null;

    if (data.model && typeof data.model === 'string') {
      llm = Services.llmService().getLlm(data.model);
    } else {
      llm = Services.llmService().getDefaultLlm();
    }

    const response = await llm.invoke(data.query);

    return this.successResponse(res, null, {
      response
    });
  }

  async rag(req: Request, res: Response): Promise<Response> {
    const data = req.body;

    this.validate(data, {
      query: 'required',
    });

    const options: RagOptions = {
      refineUserPrompt: false,
      similaritySearchResults: 5,
      model: null
    }

    if (data.refineUserPrompt !== undefined) {
      options.refineUserPrompt = data.refineUserPrompt as boolean;
    }
    if (data.similaritySearchResults !== undefined) {
      options.similaritySearchResults = data.similaritySearchResults as number;
    }
    if (data.model !== undefined) {
      options.model = data.model as string;

      // TODO: validate model
    }

    const response = await Services.aiAgent().rag(data.query, options);

    return this.successResponse(res, null, {
      response
    });
  }

}