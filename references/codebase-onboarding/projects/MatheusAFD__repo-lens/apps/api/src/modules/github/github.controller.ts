import { Controller, Get } from '@nestjs/common'
import { Session, type UserSession } from '@thallesp/nestjs-better-auth'
import { GithubService } from './github.service'

@Controller('github')
export class GithubController {
  constructor(private readonly githubService: GithubService) {}

  @Get('repos')
  async listRepos(@Session() session: UserSession) {
    const [error, repos] = await this.githubService.listUserRepos(session.user.id)
    if (error) throw error
    return repos
  }
}
