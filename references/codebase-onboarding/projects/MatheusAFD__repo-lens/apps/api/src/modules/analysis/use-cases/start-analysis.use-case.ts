import { Injectable } from '@nestjs/common'
import type { AnalysisSectionType } from '@repo/shared'
import { eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { analysis } from '../../../config/database/schema'
import { ReposService } from '../../repos/repos.service'
import { AnalysisStreamPool } from './analysis-stream-pool'
import { GetLatestAnalysisUseCase } from './get-latest-analysis.use-case'
import { RunAnalysisUseCase } from './run-analysis.use-case'

const DEFAULT_SECTIONS: AnalysisSectionType[] = [
  'executive_summary',
  'tech_stack',
  'architecture',
  'security',
  'dependencies',
  'update_plan',
  'recommendations',
  'code_metrics',
  'fun_facts',
]

const PROGRESS_SECTION: AnalysisSectionType = 'analysis_progress'

interface StartAnalysisParams {
  repoId: string
  userId: string
  sections?: AnalysisSectionType[]
  customContext?: string
}

@Injectable()
export class StartAnalysisUseCase {
  constructor(
    private readonly reposService: ReposService,
    private readonly pool: AnalysisStreamPool,
    private readonly getLatestAnalysisUseCase: GetLatestAnalysisUseCase,
    private readonly runAnalysisUseCase: RunAnalysisUseCase,
  ) {}

  async execute({
    repoId,
    userId,
    sections = DEFAULT_SECTIONS,
    customContext,
  }: StartAnalysisParams): Promise<{ analysisId: string }> {
    const [repoError, repo] = await this.reposService.getRepo(repoId, userId)
    if (repoError) throw repoError

    const previousAnalysis = await this.getLatestAnalysisUseCase.execute({ repoId, userId })
    const sectionsWithProgress = previousAnalysis
      ? [...new Set([PROGRESS_SECTION, ...sections])]
      : sections

    const [{ analysisId }] = await db
      .insert(analysis)
      .values({
        repositoryId: repo.id,
        userId,
        status: 'running',
        previousAnalysisId: previousAnalysis?.id ?? null,
      })
      .returning({ analysisId: analysis.id })

    this.pool.create(analysisId)

    this.runAnalysisUseCase
      .execute({
        analysisId,
        repo,
        userId,
        sections: sectionsWithProgress,
        customContext,
        previousAnalysis: previousAnalysis?.result ?? undefined,
      })
      .catch(async (runError: Error) => {
        await db
          .update(analysis)
          .set({
            status: 'failed',
            errorMessage: runError?.message ?? 'Unknown error',
            completedAt: new Date(),
          })
          .where(eq(analysis.id, analysisId))
        this.pool.emit(analysisId, {
          type: 'error',
          message: runError?.message ?? 'Analysis failed',
        })
        this.pool.complete(analysisId)
        this.pool.clearResult(analysisId)
      })

    return { analysisId }
  }
}
