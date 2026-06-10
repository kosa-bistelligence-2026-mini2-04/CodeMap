import { Module } from '@nestjs/common'
import { ReposController } from './repos.controller'
import { ReposService } from './repos.service'
import { GetRepoUseCase } from './use-cases/get-repo.use-case'
import { ListAnalysesUseCase } from './use-cases/list-analyses.use-case'
import { ListReposUseCase } from './use-cases/list-repos.use-case'
import { UpsertRepoUseCase } from './use-cases/upsert-repo.use-case'

@Module({
  controllers: [ReposController],
  providers: [
    ReposService,
    ListReposUseCase,
    UpsertRepoUseCase,
    GetRepoUseCase,
    ListAnalysesUseCase,
  ],
  exports: [ReposService],
})
export class ReposModule {}
