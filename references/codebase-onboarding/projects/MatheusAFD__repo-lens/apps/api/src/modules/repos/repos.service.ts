import { Injectable } from '@nestjs/common'
import { GetRepoUseCase } from './use-cases/get-repo.use-case'
import { ListAnalysesUseCase } from './use-cases/list-analyses.use-case'
import { ListReposUseCase } from './use-cases/list-repos.use-case'
import { UpsertRepoUseCase } from './use-cases/upsert-repo.use-case'

export type { UpsertRepoDto } from './use-cases/upsert-repo.use-case'

@Injectable()
export class ReposService {
  constructor(
    private readonly listReposUseCase: ListReposUseCase,
    private readonly upsertRepoUseCase: UpsertRepoUseCase,
    private readonly getRepoUseCase: GetRepoUseCase,
    private readonly listAnalysesUseCase: ListAnalysesUseCase,
  ) {}

  listRepos(userId: string) {
    return this.listReposUseCase.execute({ userId })
  }

  upsertRepo(userId: string, dto: import('./use-cases/upsert-repo.use-case').UpsertRepoDto) {
    return this.upsertRepoUseCase.execute({ userId, dto })
  }

  getRepo(repoId: string, userId: string) {
    return this.getRepoUseCase.execute({ repoId, userId })
  }

  listAnalyses(repoId: string, userId: string) {
    return this.listAnalysesUseCase.execute({ repoId, userId })
  }
}
