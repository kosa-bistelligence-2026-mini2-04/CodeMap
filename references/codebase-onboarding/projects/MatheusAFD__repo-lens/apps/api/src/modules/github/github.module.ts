import { Module } from '@nestjs/common'
import { GithubController } from './github.controller'
import { GithubService } from './github.service'
import { GetFileContentUseCase } from './use-cases/get-file-content.use-case'
import { GetRepoTreeUseCase } from './use-cases/get-repo-tree.use-case'
import { GetTokenUseCase } from './use-cases/get-token.use-case'
import { ListUserReposUseCase } from './use-cases/list-user-repos.use-case'

@Module({
  controllers: [GithubController],
  providers: [
    GithubService,
    GetTokenUseCase,
    ListUserReposUseCase,
    GetRepoTreeUseCase,
    GetFileContentUseCase,
  ],
  exports: [GithubService],
})
export class GithubModule {}
