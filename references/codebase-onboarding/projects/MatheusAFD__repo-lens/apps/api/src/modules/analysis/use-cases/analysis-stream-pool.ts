import { Injectable } from '@nestjs/common'
import type { AnalysisResult, SseEvent } from '@repo/shared'
import { SseSubjectPool } from '../../../common/streaming/sse-subject-pool'

@Injectable()
export class AnalysisStreamPool extends SseSubjectPool<SseEvent> {
  private readonly results = new Map<string, Partial<AnalysisResult>>()

  initResult(key: string): void {
    this.results.set(key, {})
  }

  setSection(key: string, name: string, data: unknown): void {
    const current = this.results.get(key) ?? {}
    this.results.set(key, { ...current, [name]: data })
  }

  getResult(key: string): Partial<AnalysisResult> {
    return this.results.get(key) ?? {}
  }

  clearResult(key: string): void {
    this.results.delete(key)
  }
}
