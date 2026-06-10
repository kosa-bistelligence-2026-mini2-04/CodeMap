import { Response } from 'express';
import HttpException from '#app/libs/exceptions/HttpException.js';
import { StdClass } from '#app/libs/types.js';

type ValidationErrors = Record<string, string>;
type ValidationData = Record<string, any>;
type ValidationRules = Record<string, string>;

export default class BaseController {

  /**
   * Sends a standard success JSON response (HTTP 200).
   */
  successResponse(res: Response, message: string | null = 'Success', data: any = null): Response {
    return res.status(200).json({
      success: true,
      message,
      data
    });
  }

  errorResponse(res: Response, message: string | null = 'Internal Server Error', error: unknown = null) {
    let errorData: null | StdClass = null;

    if (error instanceof Error) {
      errorData = {
        message: error.message,
        errorType: error.name,
        stacktrace: error instanceof Error ? error.stack?.split("\n") : null,
        cause: error.cause || null
      }
    }

    return res.status(500).json({
      success: false,
      message,
      error: errorData
    });
  }

  /** Throws a 404 Not Found HttpException. */
  notFoundException(message: string = 'Resource not found'): never {
    throw new HttpException(404, message);
  }

  /** Throws a 400 Bad Request HttpException. */
  badRequestException(message: string = 'Bad Request'): never {
    throw new HttpException(400, message);
  }

  /** Throws a 401 Unauthorized HttpException. */
  unauthorizedException(message: string = 'Unauthorized'): never {
    throw new HttpException(401, message);
  }

  /** Throws a 403 Forbidden HttpException. */
  forbiddenException(message: string = 'Forbidden'): never {
    throw new HttpException(403, message);
  }

  /** Throws a 422 Unprocessable Entity HttpException (typically for validation). */
  validationException(errors: ValidationErrors, message: string = 'Validation Failed'): never {
    throw new HttpException(422, message, errors);
  }

  /**
   * Validates data against a set of rules. Throws HttpException if validation fails.
   * 
   * @param data The input data object (e.g., req.body).
   * @param rules Validation rules (e.g., { email: 'required|email', age: 'integer' }).
   */
  validate(data: ValidationData, rules: ValidationRules): void {
    const errors: ValidationErrors = {};

    for (const field in rules) {
      if (!Object.prototype.hasOwnProperty.call(rules, field)) {
        continue;
      }

      const fieldRules: string[] = rules[field].split('|');
      const value: any = data ? data[field] : undefined;

      // Required Check
      const isRequired = fieldRules.includes('required');
      if (isRequired && (value === undefined || value === null || value === '')) {
        errors[field] = 'The field is required.';
        continue;
      }

      if (!isRequired && (value === undefined || value === null || value === '')) {
        continue;
      }

      // Array Checks
      const isArrayRule = fieldRules.includes('array');
      if (isArrayRule) {
        if (!Array.isArray(value)) {
          errors[field] = 'The field must be an array.';
          continue;
        }

        // Check array contents if specific type required (e.g., 'array|integer')
        if (fieldRules.includes('integer')) {
          for (const item of value) {
            if (!Number.isInteger(item) && !(typeof item === 'string' && /^\d+$/.test(item))) {
              errors[field] = 'The field must be an array of integers.';
              break; // Stop checking this array once one item fails
            }
          }
        } else if (fieldRules.includes('string')) {
          for (const item of value) {
            if (typeof item !== 'string') {
              errors[field] = 'The field must be an array of strings.';
              break;
            }
          }
        }
        // Add other array content types (e.g., 'array|email') if needed
        if (errors[field]) continue; // If an array content error occurred, skip non-array rules
      }

      // Non-Array Field Checks (only if 'array' rule is not present)
      if (!isArrayRule) {
        if (fieldRules.includes('string') && typeof value !== 'string') {
          errors[field] = 'The field must be a string.';
        } else if (fieldRules.includes('email')) {
          if (typeof value !== 'string' || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
            errors[field] = 'The field must be a valid email address.';
          }
        } else if (fieldRules.includes('integer')) {
          if (!Number.isInteger(value) && !(typeof value === 'string' && /^\d+$/.test(value))) {
            errors[field] = 'The field must be an integer.';
          }
        } else if (fieldRules.includes('date')) {
          // Basic YYYY-MM-DD format check & validity
          if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value) || isNaN(Date.parse(value))) {
            errors[field] = 'The field must be a valid date in YYYY-MM-DD format.';
          }
        }
      }
    }

    if (Object.keys(errors).length > 0) {
      this.validationException(errors);
    }
  }
}