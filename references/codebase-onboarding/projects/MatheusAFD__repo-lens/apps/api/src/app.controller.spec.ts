import { Test, type TestingModule } from '@nestjs/testing'

jest.mock('@thallesp/nestjs-better-auth', () => ({
  AllowAnonymous: () => () => {},
}))

import { AppController } from './app.controller'

describe('AppController', () => {
  let appController: AppController

  beforeEach(async () => {
    const app: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
    }).compile()

    appController = app.get<AppController>(AppController)
  })

  describe('health', () => {
    it('should return ok', () => {
      expect(appController.health()).toEqual({ status: 'ok' })
    })
  })
})
