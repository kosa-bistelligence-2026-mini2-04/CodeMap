import express, { Express, Request, Response, NextFunction } from 'express';
import dotenv from 'dotenv';
import bootstrap from '#core/bootstrap.js';
import initRoutes from './routes/index.js';

dotenv.config();

const portString = process.env.SERVER_PORT;
if (!portString) {
  console.error("Error: SERVER_PORT environment variable is not defined.");
  process.exit(1);
}

const port = parseInt(portString, 10);
if (isNaN(port)) {
    console.error(`Error: Invalid SERVER_PORT: "${portString}". It must be a valid number.`);
    process.exit(1);
}

async function startApp() {
  try {
    await bootstrap();
    console.log("Core bootstrap completed.");

    const httpApp: Express = express();

    // Enable CORS
    const corsMiddleware = (req: Request, res: Response, next: NextFunction): void => {
      res.header('Access-Control-Allow-Origin', '*');
      res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
      res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');

      // Handle preflight requests immediately
      if (req.method === 'OPTIONS') {
        res.sendStatus(200);
        return;
      }

      next();
    };

    httpApp.use(corsMiddleware);
    
    httpApp.use(express.json()); // for parsing application/json
    httpApp.use(express.urlencoded({ extended: true })); // for parsing application/x-www-form-urlencoded

    initRoutes(httpApp);
    console.log("Routes initialized.");

    httpApp.listen(port, () => {
      console.log(`Server is running on http://localhost:${port}`);
    });

  } catch (error) {
      console.error("Failed to start the application:", error);
      process.exit(1);
  }
}

startApp();
