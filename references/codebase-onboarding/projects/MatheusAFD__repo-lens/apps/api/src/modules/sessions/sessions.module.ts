import { Module } from '@nestjs/common'
import { SessionsController } from './sessions.controller'
import { SessionsService } from './sessions.service'
import { ListSessionsUseCase } from './use-cases/list-sessions.use-case'
import { RevokeSessionUseCase } from './use-cases/revoke-session.use-case'

@Module({
  controllers: [SessionsController],
  providers: [SessionsService, ListSessionsUseCase, RevokeSessionUseCase],
})
export class SessionsModule {}
