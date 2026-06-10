export type ApiErrorData = {
  status: number
  statusText?: string
  url?: string
  method?: string
  message?: string
  code?: number
  error?: boolean
}

export class ApiError extends Error implements ApiErrorData {
  status: number
  statusText?: string
  url?: string
  method?: string
  code?: number
  error?: boolean

  constructor(data: ApiErrorData) {
    const errorMessage = data.message || data.statusText || 'HTTP Error'
    super(errorMessage)

    this.status = data.status
    this.statusText = data.statusText
    this.url = data.url
    this.method = data.method
    this.message = errorMessage
    this.code = data.code
    this.error = data.error

    Object.setPrototypeOf(this, ApiError.prototype)

    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiError)
    } else {
      this.stack = new Error().stack
    }
  }

  toString() {
    const parts = ['HTTP Error:']
    if (this.code) parts.push(`code: ${this.code}`)
    if (this.status) parts.push(`status: ${this.status}`)
    if (this.message) parts.push(`message: '${this.message}'`)
    if (this.url) parts.push(`url: '${this.url}'`)
    if (this.method) parts.push(`method: '${this.method}'`)
    return `${parts.join(', ')}`
  }

  toJSON() {
    return {
      error: this.error,
      message: this.message,
      code: this.code,
      status: this.status,
      statusText: this.statusText,
      url: this.url,
      method: this.method,
    }
  }
}

export class AuthenticationError extends ApiError {
  constructor() {
    super({
      status: 401,
      code: 401,
      message: 'Usuário não autorizado',
      error: true,
    })
    Object.setPrototypeOf(this, AuthenticationError.prototype)
  }
}

export class ForbiddenError extends ApiError {
  constructor() {
    super({
      status: 403,
      code: 403,
      message: 'Acesso proibido',
      error: true,
    })
    Object.setPrototypeOf(this, ForbiddenError.prototype)
  }
}
