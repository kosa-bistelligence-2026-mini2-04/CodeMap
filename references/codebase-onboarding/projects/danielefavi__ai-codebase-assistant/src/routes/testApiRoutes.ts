import { Router } from 'express';
import TestController from '#app/controllers/TestController.js';
import { wrap } from '#core/controllers/utils.js';

export default function testApiRoutes(): Router {
  const router = Router();

  const loaderController = new TestController();

  router.get(
    '/',
    wrap(async (req, res, next) => {
        await loaderController.test(req, res);
    })
  );

  return router;
}