import { Injectable } from '@nestjs/common'
import type { AnalysisSectionType, AskQuestionRequest } from '@repo/shared'
import { AskQuestionUseCase } from './use-cases/ask-question.use-case'
import { GetAnalysisUseCase } from './use-cases/get-analysis.use-case'
import { GetLatestAnalysisUseCase } from './use-cases/get-latest-analysis.use-case'
import { GetQuestionsUseCase } from './use-cases/get-questions.use-case'
import { StartAnalysisUseCase } from './use-cases/start-analysis.use-case'
import { StreamAnalysisUseCase } from './use-cases/stream-analysis.use-case'

@Injectable()
export class AnalysisService {
  constructor(
    private readonly startAnalysisUseCase: StartAnalysisUseCase,
    private readonly streamAnalysisUseCase: StreamAnalysisUseCase,
    private readonly getAnalysisUseCase: GetAnalysisUseCase,
    private readonly getLatestAnalysisUseCase: GetLatestAnalysisUseCase,
    private readonly getQuestionsUseCase: GetQuestionsUseCase,
    private readonly askQuestionUseCase: AskQuestionUseCase,
  ) {}

  startAnalysis(
    repoId: string,
    userId: string,
    sections?: AnalysisSectionType[],
    customContext?: string,
  ) {
    return this.startAnalysisUseCase.execute({ repoId, userId, sections, customContext })
  }

  streamAnalysis(analysisId: string, userId: string) {
    return this.streamAnalysisUseCase.execute({ analysisId, userId })
  }

  getAnalysis(analysisId: string, userId: string) {
    return this.getAnalysisUseCase.execute({ analysisId, userId })
  }

  getLatestAnalysis(repoId: string, userId: string) {
    return this.getLatestAnalysisUseCase.execute({ repoId, userId })
  }

  getQuestions(analysisId: string, userId: string) {
    return this.getQuestionsUseCase.execute({ analysisId, userId })
  }

  askQuestion(analysisId: string, userId: string, body: AskQuestionRequest) {
    return this.askQuestionUseCase.execute({ analysisId, userId, body })
  }
}
