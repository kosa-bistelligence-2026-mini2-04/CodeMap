import express, { Express, Router, Request, Response, NextFunction, ErrorRequestHandler } from 'express';
import path from 'path';
import HttpException from '../app/libs/exceptions/HttpException.js';
import ApiException from '../app/libs/exceptions/ApiException.js';

import operationRoutes from './operationRoutes.js';
import toolRoutes from './toolRoutes.js';
import testApiRoutes from './testApiRoutes.js';
import agentRoutes from './agentRoutes.js';

export default function initRoutes(httpApp: Express): void {
  const router: Router = express.Router();

  // operationRoutes signature is: (router: Router) => Router
  httpApp.use('/api/operations', operationRoutes());
  httpApp.use('/api/tools', toolRoutes());
  httpApp.use('/api/test', testApiRoutes());
  httpApp.use('/api/agent', agentRoutes());



  // Static File Serving
  const viewsPath = path.join(process.cwd(), 'src', 'app', 'views');
  httpApp.get('/', (req: Request, res: Response) => {
    res.sendFile('index.html', { root: viewsPath });
  });

  // Serve static files from the 'public' directory under the '/public' path
  const publicPath = path.join(process.cwd(), 'public');
  httpApp.use('/public', express.static(publicPath));


  // 404 Not Found Handler: this middleware should be placed after all other route definitions
  httpApp.use((req: Request, res: Response) => {
      res.status(404).json({ message: 'Not Found' });
  });

  // Global Error Handler
  const globalErrorHandler: ErrorRequestHandler = async (err: unknown, req: Request, res: Response, next: NextFunction) => {
  console.error("Global Error Handler caught:", err);

    // Default error details
    let status: number = 500;
    let message: string = 'Internal Server Error';
    let data: any = null;
    let errors: any = null;
    let cause: unknown = null;
    let errorType: string = 'Error'; // Default

    if (err instanceof HttpException) {
      // Type is automatically narrowed to HttpException within this block
      status = err.statusCode;
      message = err.message;
      errors = err.errors; // Direct access, no 'as' needed
      errorType = err.name; // Usually 'HttpException'
    }
    else if (err instanceof ApiException) {
      status = err.statusCode;
      errorType = err.name;
      try {
        message = await err.getBodyMessage();
        data = await err.getBodyResponse();
      } catch (e) {
        console.error("Error getting details from ApiException:", e);
        message = err.message || "Failed to retrieve API exception details.";
      }
    }
    else if (err instanceof Error) {
      message = err.message;
      errorType = err.name;
      cause = err.cause;
    }

    if (typeof message !== 'string') {
      message = 'An unknown error occurred.';
    }

    res.status(status).json({
        message,
        errorType,
        stacktrace: process.env.NODE_ENV !== 'production' && err instanceof Error ? err.stack?.split("\n") : undefined,
        cause,
        data,
        errors
    });
  };

  httpApp.use(globalErrorHandler);
}