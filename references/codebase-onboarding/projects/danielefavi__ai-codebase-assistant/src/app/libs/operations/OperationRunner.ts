import Document from "#app/models/Document.js";
import { StdClass } from "../types.js";
import { RunnerResult } from "../types.js";
import ChunkContentOperation from "./ChunkContentOperation.js";
import AbstractOperation from "./AbstractOperation.js";
import StoreInVectorDbOperation from "./StoreInVectorDbOperation.js";
import SummarizeContentOperation from "./SummarizeContentOperation.js";

export default class OperationRunner {
  private registry: Map<string, new () => AbstractOperation>;

  constructor() {
    this.registry = new Map();
    this.registerOperations();
  }

  /**
   * Registers the standard operations. Call this in the constructor or manually.
   */
  private registerOperations(): void {
    this.registerOperation(ChunkContentOperation.operationName, ChunkContentOperation);
    this.registerOperation(SummarizeContentOperation.operationName, SummarizeContentOperation);
    this.registerOperation(StoreInVectorDbOperation.operationName, StoreInVectorDbOperation);
  }

  /**
   * Allows adding new operations dynamically or replacing existing ones.
   * 
   * @param name The string identifier for the operation (matching the DB value).
   * @param operationClass The class implementing AbstractOperation.
   */
  public registerOperation(name: string, operationClass: new () => AbstractOperation): void {
    if (this.registry.has(name)) {
        console.warn(`[Runner] Operation "${name}" is already registered. Overwriting.`);
    }
    this.registry.set(name, operationClass);
    console.log(`[Runner] Registered operation: ${name}`);
  }

  public async run(document: Document, extra: StdClass = {}): Promise<RunnerResult> {
    if (!document.operations) {
      return {
        success: true,
        message: 'No operation set',
        results: []
      };
    }

    if (document.isStatusLocked()) {
      throw new Error(`The document record is locked at the current time.`, {
        documentId: document.id
      } as StdClass);
    }

    document.setStatusLock();

    console.log(`\n[Runner] Starting processing for record ID: ${document.id}`);

    let currentDocState = document;

    const runnerResult = {
      success: true,
      message: null,
      results: []
    } as RunnerResult;

    for (const [opName, opStatus] of Object.entries(document.operations)) {
      if (opStatus === Document.OPERATION_STATUS.SUCCESS) {
        runnerResult.results.push({
          success: true,
          message: `Operation already executed, skipping it.`,
          name: opName, 
          error: null
        });
        continue;
      }

      try {
        const OperationClass = this.registry.get(opName);

        if (!OperationClass) {
          throw new Error(`The operation ${opName} is not registered.`);
        }

        const operationInstance = new OperationClass();
      
        const opResult = await operationInstance.run(currentDocState, extra);
        console.log(`Operation result for ${opName} `, opResult);
        if (!opResult.success) {
          console.error(`The  ${opName} failed`, opResult);
          throw new Error(`The operation ${opName} failed`);
        }

        document.operationSuccess(opName);

        runnerResult.results.push(opResult);
      } catch (error) {
        document.operationError(opName);

        console.error(`[Runner] Error executing operation "${opName}" for record ID ${document.id}.`, error);

        const msgError = error instanceof Error ? error.message : '';
        
        runnerResult.results.push({
          success: false,
          message: `Error executing operation "${opName}" for record ID ${document.id} ` + msgError,
          name: opName, 
          error: error
        });

        break;
      }
    }

    console.log(`[Runner] Finished processing for record ID: ${document.id}`);
    return runnerResult;
  }

}