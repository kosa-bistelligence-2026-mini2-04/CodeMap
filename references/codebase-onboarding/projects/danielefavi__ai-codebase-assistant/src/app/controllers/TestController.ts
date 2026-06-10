import { Request, Response } from 'express';
import BaseController from './BaseController.js';
import { StdClass } from '#app/libs/types.js';
import Services from '#app/libs/Services.js';
import Document from '#app/models/Document.js';

export default class TestController extends BaseController {

  async test(req: Request, res: Response): Promise<Response> {
    try {
      return this.successResponse(res, 'Hello', {
        msg: 'Make your tests here'
      });
    } catch (error) {
      return this.errorResponse(res, 'error occurred', error);
    }
  }

}