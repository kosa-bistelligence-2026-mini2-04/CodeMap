import type { HttpClient } from '@/types/http'
import { FetchHttpClientAdapter } from '../adapters/fetch-adapter'

export const httpHttpClientFactory = (baseUrl?: string): HttpClient =>
  new FetchHttpClientAdapter(baseUrl)
