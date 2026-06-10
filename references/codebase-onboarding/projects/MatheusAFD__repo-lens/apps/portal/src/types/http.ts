import type { ApiError } from '@/services/error'

export type RequestConfig = {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
  params?: Record<string, string>
}

export type ResponseHeaders = {
  get: (name: string) => string
}

export type Response<T> = {
  data: T
  status: number
  headers: ResponseHeaders
}

export type HttpClient = {
  request<T>(config: RequestConfig): Promise<[ApiError | null, Response<T> | null]>
}
