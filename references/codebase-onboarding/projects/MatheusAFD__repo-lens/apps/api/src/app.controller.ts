import { Controller, Get } from '@nestjs/common'
import { AllowAnonymous } from '@thallesp/nestjs-better-auth'

@Controller()
export class AppController {
  @Get('health')
  @AllowAnonymous()
  health() {
    return { status: 'ok' }
  }
}
