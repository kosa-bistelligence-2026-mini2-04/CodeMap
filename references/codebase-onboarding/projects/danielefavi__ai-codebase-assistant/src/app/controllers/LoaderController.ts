import { Request, Response } from 'express';
import BaseController from './BaseController.js';
import MasterOperation from '#app/libs/operations/MasterOperation.js';
import OperationRunner from '#app/libs/operations/OperationRunner.js';
import DocumentRepo from '#app/repositories/DocumentRepo.js';
import Document from '#app/models/Document.js';
import Services from '#app/libs/Services.js';

export default class LoaderController extends BaseController {

  async execMasterOperation(req: Request, res: Response): Promise<Response> {
    // @TODO: the parameters foldersToScan and fileExtensionList should come from the request
    const loader = new MasterOperation(['./source-code'], ['js', 'txt', 'md']);

    const chunks = await loader.loadDbMasterData(['chunkContent', 'summarizeContent', 'storeInVectorDb']);

    return this.successResponse(res, null, chunks);
  }


  async runRandomOperations(req: Request, res: Response): Promise<Response> {
    // pick up a random record
    const document = await DocumentRepo.getRandomDocument({
      status: Document.DOCUMENT_STATUS.TO_PROCESS
    });

    if (!document) {
      return this.successResponse(res, 'No operations to process found');
    }

    const runner = new OperationRunner();
    const opResult = await runner.run(document);

    return this.successResponse(res, 'Executed', opResult);
  }

  async reset(req: Request, res: Response): Promise<Response> {
    await Services.vectorStore().deleteEverything();

    await Document.destroy({ truncate: true });

    return this.successResponse(res, 'Collection deleted and recreated');
  }

}