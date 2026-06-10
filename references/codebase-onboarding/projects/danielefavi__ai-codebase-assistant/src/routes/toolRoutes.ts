import { Router } from 'express';
import { wrap } from '#core/controllers/utils.js';
import ToolController from '#app/controllers/ToolController.js';

export default function loaderApiRoutes(): Router {
  const router = Router();

  const toolController = new ToolController();

  router.get(
    '/vector-store/get-latest-entries',
    wrap(async (req, res, next) => {
        await toolController.getLatestEntries(req, res);
    })
  );

  router.get(
    '/ollama/models',
    wrap(async (req, res, next) => {
        await toolController.getModels(req, res);
    })
  );

  return router;
}