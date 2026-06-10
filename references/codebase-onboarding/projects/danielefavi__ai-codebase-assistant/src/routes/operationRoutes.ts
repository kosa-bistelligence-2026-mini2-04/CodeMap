import { Router } from 'express';
import { wrap } from '#core/controllers/utils.js';
import LoaderController from '#app/controllers/LoaderController.js';

export default function loaderApiRoutes(): Router {
  const router = Router();
  const loaderController = new LoaderController();

  router.post(
    '/run-master',
    wrap(async (req, res, next) => {
        await loaderController.execMasterOperation(req, res);
    })
  );

  router.post(
    '/run-rand',
    wrap(async (req, res, next) => {
        await loaderController.runRandomOperations(req, res);
    })
  );

  router.post(
    '/reset',
    wrap(async (req, res, next) => {
        await loaderController.reset(req, res);
    })
  );

  return router;
}