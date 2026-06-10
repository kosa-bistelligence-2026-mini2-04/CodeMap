/**
 * Represents an error originating from an API response.
 * Wraps the original Fetch Response and provides helpers to extract error details.
 */
export default class ApiException extends Error {
  /** The original Fetch API Response object. */
  public readonly response: Response;

  /** Cached response body (parsed JSON object, text, or null if not yet read). */
  private parsedBody: unknown | string | null = null;

  /**
   * Creates an instance of ApiException.
   * 
   * @param response The Fetch Response object.
   */
  constructor(response: Response) {
    super(`API request failed with status ${response.status} (${response.statusText || 'No status text'})`);

    this.name = 'ApiException';
    this.response = response;

    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }

  /**
   * Retrieves the response body, attempting to parse it as JSON.
   * Caches the result to avoid reading the response stream multiple times.
   * 
   * @returns A promise resolving to the parsed JSON object (typed as unknown) or the raw text string.
   */
  async getBodyResponse(): Promise<unknown | string> {
    // Return cached data if available
    if (this.parsedBody !== null) {
      return this.parsedBody;
    }

    let bodyText: string;
    try {
      bodyText = await this.response.text();
    } catch (e: unknown) {
      console.error("ApiException: Failed to read response body text.", e instanceof Error ? e.message : e);
      this.parsedBody = "";
      return this.parsedBody;
    }

    try {
      this.parsedBody = JSON.parse(bodyText);
    } catch (e) {
      this.parsedBody = bodyText;
    }

    return this.parsedBody;
  }

  /**
   * Attempts to extract a user-friendly error message from the response body.
   * Looks for common properties like 'message' or 'error' in JSON responses,
   * uses the response text if not JSON, or falls back to the initial error message.
   * 
   * @returns A promise resolving to the extracted or default error message string.
   */
  async getBodyMessage(): Promise<string> {
    const body = await this.getBodyResponse();

    if (body && typeof body === 'object') {
      if ('message' in body && typeof body.message === 'string') {
        return body.message;
      }
      if ('error' in body && typeof body.error === 'string') {
        return body.error;
      }
      // Add checks for other potential error fields if necessary
      // if ('detail' in body && typeof body.detail === 'string') {
      //   return body.detail;
      // }
    }

    if (typeof body === 'string' && body.trim().length > 0) {
      return body;
    }

    return this.message;
  }

  /**
   * Convenience getter for the HTTP status code from the response.
   * 
   * @returns The HTTP status code number.
   */
  public get statusCode(): number {
    return this.response.status;
  }
}