import { Request, Response, NextFunction } from 'express';

type AsyncExpressHandler = (req: Request, res: Response, next: NextFunction) => Promise<any>;

// Wrapper function for async route handlers to catch errors and pass them to next()
export const wrap = (fn: AsyncExpressHandler) =>
  (req: Request, res: Response, next: NextFunction) => {
    // Make sure the promise chain is caught and errors forwarded
    Promise.resolve(fn(req, res, next)).catch(next);
  };
