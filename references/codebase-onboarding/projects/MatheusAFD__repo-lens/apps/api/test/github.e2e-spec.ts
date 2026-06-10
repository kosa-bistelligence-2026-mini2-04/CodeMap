import { Test, type TestingModule } from '@nestjs/testing'
import type { INestApplication } from '@nestjs/common'
import request from 'supertest'
import type { App } from 'supertest/types'
import { AppModule } from '../src/app.module'

const TEST_USER = {
  name: 'E2E GitHub User',
  email: `e2e-github-${Date.now()}@repo-lens.dev`,
  password: 'TestPassword123',
}

async function createAuthenticatedSession(app: INestApplication<App>): Promise<string> {
  await request(app.getHttpServer()).post('/api/auth/sign-up/email').send(TEST_USER)

  const signinRes = await request(app.getHttpServer())
    .post('/api/auth/sign-in/email')
    .send({ email: TEST_USER.email, password: TEST_USER.password })

  const setCookie = signinRes.headers['set-cookie'] as string | string[]
  const cookies = Array.isArray(setCookie) ? setCookie : [setCookie]
  return cookies.join('; ')
}

describe('GithubController (e2e)', () => {
  let app: INestApplication<App>
  let sessionCookie: string

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile()

    app = moduleFixture.createNestApplication()
    await app.init()

    sessionCookie = await createAuthenticatedSession(app)
  })

  afterAll(async () => {
    await app.close()
  })

  describe('GET /github/repos', () => {
    it('returns 401 without auth session', () => {
      return request(app.getHttpServer()).get('/github/repos').expect(401)
    })

    it('returns 401 when authenticated but no github account linked', () => {
      return request(app.getHttpServer())
        .get('/github/repos')
        .set('Cookie', sessionCookie)
        .expect(401)
    })
  })
})
