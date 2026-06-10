import Document from "#app/models/Document.js";
import { OperationResult, StdClass } from "../types.js";

export default abstract class AbstractOperation {
  public static readonly operationName: string;
  abstract performOperation(record: Document, extra: StdClass): Promise<OperationResult>;

  async run(record: Document, extra: StdClass = {}): Promise<OperationResult> {
    const operationName = (this.constructor as typeof AbstractOperation).operationName;

    try {
      const operationResult = await this.performOperation(record, extra);

      await record.operationSuccess(operationName);

      return operationResult;
    } catch (error) {      
      return {
        success: false,
        message: 'The operation terminated with error',
        name: operationName, 
        error
      } as OperationResult;
    }
  }

  successResponse(message: string): OperationResult {
    return {
      success: true,
      message: message,
      name: (this.constructor as typeof AbstractOperation).operationName, 
      error: null
    }
  }

  errorResponse(message: string, error: unknown = null): OperationResult {
    return {
      success: false,
      message: message,
      name: (this.constructor as typeof AbstractOperation).operationName, 
      error
    }
  }

}