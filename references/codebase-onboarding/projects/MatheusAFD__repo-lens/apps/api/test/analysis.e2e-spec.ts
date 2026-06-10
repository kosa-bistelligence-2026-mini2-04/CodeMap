import { Test, type TestingModule } from '@nestjs/testing'
import type { INestApplication } from '@nestjs/common'
import request from 'supertest'
import type { App } from 'supertest/types'
import { AppModule } from '../src/app.module'

const TEST_USER = {
  name: 'E2E Analysis User',
  email: `e2e-analysis-${Date.now()}@repo-lens.dev`,
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

async function createRepo(app: INestApplication<App>, sessionCookie: string): Promise<string> {
  const res = await request(app.getHttpServer())
    .post('/repos')
    .set('Cookie', sessionCookie)
    .send({
      githubRepoId: String(Date.now()),
      owner: 'test-owner',
      name: 'analysis-e2e-repo',
      fullName: 'test-owner/analysis-e2e-repo',
      language: 'TypeScript',
      isPrivate: false,
      htmlUrl: 'https://github.com/test-owner/analysis-e2e-repo',
    })
  return res.body.id
}

describe('AnalysisController (e2e)', () => {
  let app: INestApplication<App>
  let sessionCookie: string
  let repoId: string

  beforeAll(async () => {
    process.env.ANTHROPIC_MOCK = 'true'

    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile()

    app = moduleFixture.createNestApplication()
    await app.init()

    sessionCookie = await createAuthenticatedSession(app)
    repoId = await createRepo(app, sessionCookie)
  })

  afterAll(async () => {
    process.env.ANTHROPIC_MOCK = undefined
    await app.close()
  })

  describe('POST /analysis/:repoId/start', () => {
    it('returns 401 without auth session', () => {
      return request(app.getHttpServer()).post(`/analysis/${repoId}/start`).expect(401)
    })

    it('returns 404 when repoId does not exist', () => {
      return request(app.getHttpServer())
        .post('/analysis/00000000-0000-0000-0000-000000000000/start')
        .set('Cookie', sessionCookie)
        .expect(404)
    })

    it('returns 201 with analysisId UUID for valid repoId', () => {
      return request(app.getHttpServer())
        .post(`/analysis/${repoId}/start`)
        .set('Cookie', sessionCookie)
        .expect(201)
        .expect((res) => {
          expect(res.body).toHaveProperty('analysisId')
          expect(typeof res.body.analysisId).toBe('string')
        })
    })
  })

  describe('GET /analysis/:id', () => {
    let analysisId: string

    beforeAll(async () => {
      const startRes = await request(app.getHttpServer())
        .post(`/analysis/${repoId}/start`)
        .set('Cookie', sessionCookie)
      analysisId = startRes.body.analysisId
    })

    it('returns 401 without auth session', () => {
      return request(app.getHttpServer()).get(`/analysis/${analysisId}`).expect(401)
    })

    it('returns 404 for non-existent analysisId', () => {
      return request(app.getHttpServer())
        .get('/analysis/00000000-0000-0000-0000-000000000000')
        .set('Cookie', sessionCookie)
        .expect(404)
    })

    it('returns 200 with analysis for own analysisId', () => {
      return request(app.getHttpServer())
        .get(`/analysis/${analysisId}`)
        .set('Cookie', sessionCookie)
        .expect(200)
        .expect((res) => {
          expect(res.body.id).toBe(analysisId)
        })
    })
  })

  describe('GET /analysis/repo/:repoId/latest', () => {
    it('returns 401 without auth session', () => {
      return request(app.getHttpServer()).get(`/analysis/repo/${repoId}/latest`).expect(401)
    })

    it('returns null when no completed analyses exist', async () => {
      const freshRepoId = await createRepo(app, sessionCookie)

      return request(app.getHttpServer())
        .get(`/analysis/repo/${freshRepoId}/latest`)
        .set('Cookie', sessionCookie)
        .expect(200)
        .expect((res) => {
          expect(res.body).toBeNull()
        })
    })
  })

  describe('GET /analysis/:id/stream', () => {
    it('returns 401 without auth session', () => {
      return request(app.getHttpServer()).get('/analysis/some-id/stream').expect(401)
    })

    it('responds with text/event-stream content type', async () => {
      const streamRepoId = await createRepo(app, sessionCookie)

      const startRes = await request(app.getHttpServer())
        .post(`/analysis/${streamRepoId}/start`)
        .set('Cookie', sessionCookie)

      const { analysisId } = startRes.body

      return request(app.getHttpServer())
        .get(`/analysis/${analysisId}/stream`)
        .set('Cookie', sessionCookie)
        .expect((res) => {
          expect(res.headers['content-type']).toMatch(/text\/event-stream/)
        })
    })
  })
})
