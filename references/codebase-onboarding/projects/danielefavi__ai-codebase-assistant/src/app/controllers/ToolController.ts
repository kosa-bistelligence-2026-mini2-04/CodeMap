import { Request, Response } from 'express';
import BaseController from './BaseController.js';
import dotenv from 'dotenv';
import Services from '#app/libs/Services.js';

dotenv.config();

export default class ToolController extends BaseController {

  async getLatestEntries(req: Request, res: Response): Promise<Response> {
    const data = await Services.vectorStore().getLatestEntries(50);

    return this.successResponse(res, null, data);
  }

  async getModels(req: Request, res: Response): Promise<Response> {
    const data = await Services.llmService().getModels();

    return this.successResponse(res, null, data);
  }

}