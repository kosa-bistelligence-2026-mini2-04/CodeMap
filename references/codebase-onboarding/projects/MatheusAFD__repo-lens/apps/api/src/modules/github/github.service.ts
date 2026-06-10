import { Injectable } from '@nestjs/common'
import { GetFileContentUseCase } from './use-cases/get-file-content.use-case'
import { GetRepoTreeUseCase } from './use-cases/get-repo-tree.use-case'
import { GetTokenUseCase } from './use-cases/get-token.use-case'
import { ListUserReposUseCase } from './use-cases/list-user-repos.use-case'

export type { GithubRepo, GithubTreeItem } from './github.types'

@Injectable()
export class GithubService {
  constructor(
    private readonly getTokenUseCase: GetTokenUseCase,
    private readonly listUserReposUseCase: ListUserReposUseCase,
    private readonly getRepoTreeUseCase: GetRepoTreeUseCase,
    private readonly getFileContentUseCase: GetFileContentUseCase,
  ) {}

  getToken(userId: string) {
    return this.getTokenUseCase.execute({ userId })
  }

  listUserRepos(userId: string) {
    return this.listUserReposUseCase.execute({ userId })
  }

  getRepoTree(owner: string, repo: string, token: string) {
    return this.getRepoTreeUseCase.execute({ owner, repo, token })
  }

  getFileContent(owner: string, repo: string, path: string, token: string) {
    return this.getFileContentUseCase.execute({ owner, repo, path, token })
  }
}
