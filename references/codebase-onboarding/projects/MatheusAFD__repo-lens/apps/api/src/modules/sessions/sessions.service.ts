import { Injectable } from '@nestjs/common'
import { ListSessionsUseCase } from './use-cases/list-sessions.use-case'
import { RevokeSessionUseCase } from './use-cases/revoke-session.use-case'

@Injectable()
export class SessionsService {
  constructor(
    private readonly listSessionsUseCase: ListSessionsUseCase,
    private readonly revokeSessionUseCase: RevokeSessionUseCase,
  ) {}

  listSessions() {
    return this.listSessionsUseCase.execute()
  }

  revokeSession(token: string) {
    return this.revokeSessionUseCase.execute({ token })
  }
}
