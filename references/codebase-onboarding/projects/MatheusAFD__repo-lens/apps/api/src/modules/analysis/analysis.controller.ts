import { Body, Controller, Get, Param, Post, Sse } from '@nestjs/common'
import { Throttle } from '@nestjs/throttler'
import type { Observable } from 'rxjs'
import { Session, type UserSession } from '@thallesp/nestjs-better-auth'
import type { AskQuestionRequest, StartAnalysisRequest } from '@repo/shared'
import { AnalysisService } from './analysis.service'

@Controller('analysis')
export class AnalysisController {
  constructor(private readonly analysisService: AnalysisService) {}

  @Throttle({ analysis: { ttl: 60_000, limit: 5 } })
  @Post(':repoId/start')
  startAnalysis(
    @Param('repoId') repoId: string,
    @Body() body: StartAnalysisRequest,
    @Session() session: UserSession,
  ) {
    return this.analysisService.startAnalysis(
      repoId,
      session.user.id,
      body?.sections,
      body?.customContext,
    )
  }

  @Get(':id/stream')
  @Sse()
  streamAnalysis(
    @Param('id') id: string,
    @Session() session: UserSession,
  ): Promise<Observable<MessageEvent>> {
    return this.analysisService.streamAnalysis(id, session.user.id)
  }

  @Get(':id')
  getAnalysis(@Param('id') id: string, @Session() session: UserSession) {
    return this.analysisService.getAnalysis(id, session.user.id)
  }

  @Get('repo/:repoId/latest')
  getLatestAnalysis(@Param('repoId') repoId: string, @Session() session: UserSession) {
    return this.analysisService.getLatestAnalysis(repoId, session.user.id)
  }
  @Get(':id/questions')
  getQuestions(@Param('id') id: string, @Session() session: UserSession) {
    return this.analysisService.getQuestions(id, session.user.id)
  }

  @Throttle({ analysis: { ttl: 60_000, limit: 5 } })
  @Post(':id/ask')
  @Sse()
  askQuestion(
    @Param('id') id: string,
    @Body() body: AskQuestionRequest,
    @Session() session: UserSession,
  ): Promise<Observable<MessageEvent>> {
    return this.analysisService.askQuestion(id, session.user.id, body)
  }
}
