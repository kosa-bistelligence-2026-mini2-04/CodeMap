import { Body, Controller, Get, Param, Post } from '@nestjs/common'
import { Session, type UserSession } from '@thallesp/nestjs-better-auth'
import { ReposService, type UpsertRepoDto } from './repos.service'

@Controller('repos')
export class ReposController {
  constructor(private readonly reposService: ReposService) {}

  @Get()
  listRepos(@Session() session: UserSession) {
    return this.reposService.listRepos(session.user.id)
  }

  @Post()
  async upsertRepo(@Session() session: UserSession, @Body() dto: UpsertRepoDto) {
    const [error, repo] = await this.reposService.upsertRepo(session.user.id, dto)
    if (error) throw error
    return repo
  }

  @Get(':id')
  async getRepo(@Param('id') id: string, @Session() session: UserSession) {
    const [error, repo] = await this.reposService.getRepo(id, session.user.id)
    if (error) throw error
    return repo
  }

  @Get(':id/analyses')
  listAnalyses(@Param('id') id: string, @Session() session: UserSession) {
    return this.reposService.listAnalyses(id, session.user.id)
  }
}
