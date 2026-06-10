import { Router } from 'express';
import { wrap } from '#core/controllers/utils.js';
import AgentController from '#app/controllers/AgentController.js';

export default function agentRoutes(): Router {

  const router = Router();
  const agentController = new AgentController();

  router.post(
    '/ask-stream',
    wrap(async (req, res, next) => {
      await agentController.genericQuestionStream(req, res);
    })
  );

  router.post(
    '/ask',
    wrap(async (req, res, next) => {
      await agentController.genericQuestion(req, res);
    })
  );

  router.post(
    '/rag',
    wrap(async (req, res, next) => {
      await agentController.rag(req, res);
    })
  );

  return router;
}