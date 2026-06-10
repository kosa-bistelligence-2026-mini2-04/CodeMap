import { Module } from '@nestjs/common'
import { ThrottlerModule } from '@nestjs/throttler'
import { AuthModule } from '@thallesp/nestjs-better-auth'
import { AppController } from './app.controller'
import { auth } from './auth/auth'
import { AnalysisModule } from './modules/analysis/analysis.module'
import { ChatModule } from './modules/chat/chat.module'
import { GithubModule } from './modules/github/github.module'
import { ReposModule } from './modules/repos/repos.module'
import { SessionsModule } from './modules/sessions/sessions.module'

@Module({
  imports: [
    ThrottlerModule.forRoot([
      {
        name: 'analysis',
        ttl: 60_000,
        limit: 5,
      },
      {
        name: 'chat',
        ttl: 60_000,
        limit: 15,
      },
    ]),
    AuthModule.forRoot({ auth }),
    SessionsModule,
    GithubModule,
    ReposModule,
    AnalysisModule,
    ChatModule,
  ],
  controllers: [AppController],
})
export class AppModule {}
