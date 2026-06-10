import { Controller, Delete, Get, Param } from '@nestjs/common'
import { Roles } from '@thallesp/nestjs-better-auth'
import { SessionsService } from './sessions.service'

@Controller('sessions')
@Roles(['backoffice'])
export class SessionsController {
  constructor(private readonly sessionsService: SessionsService) {}

  @Get()
  async listSessions() {
    return this.sessionsService.listSessions()
  }

  @Delete(':token')
  async revokeSession(@Param('token') token: string) {
    return this.sessionsService.revokeSession(token)
  }
}
