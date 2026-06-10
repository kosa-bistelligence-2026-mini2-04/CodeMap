type ExceptionErrors = Record<string, any> | null;

export default class HttpException extends Error {
    public statusCode: number;
    public errors: ExceptionErrors;

    constructor(statusCode: number, message: string | null = null, errors: ExceptionErrors = null) {
        const finalMessage = HttpException.determineMessage(statusCode, message);
        super(finalMessage);

        this.statusCode = statusCode;
        this.errors = errors;
        this.name = 'HttpException';

        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, this.constructor);
        }
    }

    /**
     * Static helper method to determine the appropriate error message.
     * It prioritizes the provided message, otherwise uses defaults based on statusCode.
     * Made static because it doesn't rely on instance state ('this').
     *
     * @param statusCode - The HTTP status code.
     * @param providedMessage - The message passed to the constructor, if any.
     * @returns The message string to be used for the error.
     */
    private static determineMessage(statusCode: number, providedMessage: string | null): string {
        if (providedMessage) {
            return providedMessage;
        }

        switch (statusCode) {
            case 400:
                return 'Bad Request';
            case 401:
                return 'Unauthorized';
            case 403:
                return 'Forbidden';
            case 404:
                return 'Not Found';
            case 422:
                return 'Unprocessable Entity / Validation Error';
            case 500:
                return 'Internal Server Error';
            default:
                if (statusCode >= 500) return `Server Error (${statusCode})`;
                if (statusCode >= 400) return `Client Error (${statusCode})`;
                return `An unexpected error occurred (${statusCode})`;
        }
    }
}