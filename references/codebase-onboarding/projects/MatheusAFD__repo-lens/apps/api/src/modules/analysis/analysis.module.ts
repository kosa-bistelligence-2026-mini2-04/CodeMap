import { Module } from '@nestjs/common'
import { GithubModule } from '../github/github.module'
import { ReposModule } from '../repos/repos.module'
import { AnalysisController } from './analysis.controller'
import { AnalysisService } from './analysis.service'
import { ContextBuilderService } from './context-builder.service'
import { PromptBuilderService } from './prompt-builder.service'
import { AnalysisStreamPool } from './use-cases/analysis-stream-pool'
import { AskQuestionUseCase } from './use-cases/ask-question.use-case'
import { GetAnalysisUseCase } from './use-cases/get-analysis.use-case'
import { GetLatestAnalysisUseCase } from './use-cases/get-latest-analysis.use-case'
import { GetQuestionsUseCase } from './use-cases/get-questions.use-case'
import { RunAnalysisUseCase } from './use-cases/run-analysis.use-case'
import { StartAnalysisUseCase } from './use-cases/start-analysis.use-case'
import { StreamAnalysisUseCase } from './use-cases/stream-analysis.use-case'

@Module({
  imports: [GithubModule, ReposModule],
  controllers: [AnalysisController],
  providers: [
    AnalysisService,
    ContextBuilderService,
    PromptBuilderService,
    AnalysisStreamPool,
    StartAnalysisUseCase,
    StreamAnalysisUseCase,
    GetAnalysisUseCase,
    GetLatestAnalysisUseCase,
    GetQuestionsUseCase,
    AskQuestionUseCase,
    RunAnalysisUseCase,
  ],
  exports: [AnalysisService, ContextBuilderService],
})
export class AnalysisModule {}
