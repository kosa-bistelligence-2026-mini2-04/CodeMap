import { HttpStatusCodes } from '@/common/constants/http-status-code'
import { logger } from '@/common/utils/logger'
import { env } from '@/env'
import type { HttpClient, RequestConfig, Response, ResponseHeaders } from '@/types/http'
import { ApiError } from '../error'

const isServer = typeof window === 'undefined'

export class FetchHttpClientAdapter implements HttpClient {
  private baseURL: string

  constructor(baseURL = '') {
    this.baseURL = baseURL
  }

  async request<ResponseData = unknown>(
    config: RequestConfig,
  ): Promise<[ApiError | null, Response<ResponseData> | null]> {
    const isFormData = config.body instanceof FormData

    const headers: Record<string, string> = {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...config.headers,
    }

    const requestOptions: RequestInit = {
      method: config.method.toUpperCase(),
      headers,
      credentials: 'include',
    }

    if (config.body && ['POST', 'PUT', 'PATCH'].includes(config.method.toUpperCase())) {
      requestOptions.body = isFormData ? (config.body as FormData) : JSON.stringify(config.body)
    }

    let url = this.baseURL ? `${this.baseURL}${config.url}` : config.url

    if (config.params) {
      const queryString = new URLSearchParams(config.params as Record<string, string>).toString()
      url = `${url}?${queryString}`
    }

    if (isServer && url.startsWith('/')) {
      const baseUrl = env.VITE_API_URL || 'http://0.0.0.0:3000'
      url = `${baseUrl}${url}`
    }

    const method = config.method.toUpperCase()
    const startTime = Date.now()

    logger.info({ method, url }, 'HTTP Request Starting')

    try {
      const response = await fetch(url, requestOptions)

      if (!response.ok) {
        const duration = Date.now() - startTime
        let errorData: { error?: boolean; message?: string; code?: number } = {}

        try {
          errorData = await response.json()
        } catch {}

        const error = new ApiError({
          status: response.status,
          statusText: response.statusText,
          url,
          method,
          error: errorData.error ?? true,
          message: errorData.message,
          code: errorData.code ?? response.status,
        })

        logger.error(
          {
            method,
            url,
            status: response.status,
            duration,
            message: errorData.message || response.statusText,
          },
          'HTTP Request Error',
        )

        return [error, null]
      }

      const data: ResponseData = await response.json()
      const duration = Date.now() - startTime

      const responseHeaders: ResponseHeaders = {
        get: (headerName: string) => response.headers.get(headerName) || '',
      } as ResponseHeaders

      logger.info(
        {
          method,
          url,
          status: response.status,
          duration,
        },
        'HTTP Request Success',
      )

      return [
        null,
        {
          data,
          status: response.status,
          headers: responseHeaders,
        },
      ]
    } catch (error) {
      const duration = Date.now() - startTime

      if (error instanceof ApiError) {
        logger.error(
          {
            method,
            url,
            duration,
            error: error.message,
          },
          'HTTP Request ApiError',
        )
        return [error, null]
      }

      const apiError = new ApiError({
        status: HttpStatusCodes.INTERNAL_SERVER_ERROR,
        statusText: 'Internal Server Error',
        url,
        method,
        message: error instanceof Error ? error.message : 'Unknown error',
      })

      logger.error(
        {
          method,
          url,
          duration,
          error: error instanceof Error ? error.message : String(error),
        },
        'HTTP Request Exception',
      )

      return [apiError, null]
    }
  }
}
