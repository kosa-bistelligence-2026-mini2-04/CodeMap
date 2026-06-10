import { Test, type TestingModule } from '@nestjs/testing'
import type { INestApplication } from '@nestjs/common'
import request from 'supertest'
import type { App } from 'supertest/types'
import { AppModule } from '../src/app.module'

const TEST_USER = {
  name: 'E2E Repos User',
  email: `e2e-repos-${Date.now()}@repo-lens.dev`,
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

const SAMPLE_REPO_DTO = {
  githubRepoId: `sample-${Date.now()}`,
  owner: 'test-owner',
  name: 'e2e-test-repo',
  fullName: 'test-owner/e2e-test-repo',
  description: 'E2E test repository',
  language: 'TypeScript',
  isPrivate: false,
  htmlUrl: 'https://github.com/test-owner/e2e-test-repo',
}

describe('ReposController (e2e)', () => {
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

  describe('GET /repos', () => {
    it('returns 401 without auth session', () => {
      return request(app.getHttpServer()).get('/repos').expect(401)
    })

    it('returns 200 with empty array for new authenticated user', () => {
      return request(app.getHttpServer())
        .get('/repos')
        .set('Cookie', sessionCookie)
        .expect(200)
        .expect((res) => {
          expect(Array.isArray(res.body)).toBe(true)
        })
    })
  })

  describe('POST /repos', () => {
    it('returns 401 without auth session', () => {
      return request(app.getHttpServer()).post('/repos').send(SAMPLE_REPO_DTO).expect(401)
    })

    it('returns 201 with created repo on valid payload', () => {
      const dto = { ...SAMPLE_REPO_DTO, githubRepoId: String(Date.now()) }

      return request(app.getHttpServer())
        .post('/repos')
        .set('Cookie', sessionCookie)
        .send(dto)
        .expect(201)
        .expect((res) => {
          expect(res.body).toHaveProperty('id')
          expect(res.body.name).toBe(dto.name)
          expect(res.body.owner).toBe(dto.owner)
        })
    })

    it('returns 200 (upsert) when posting same githubRepoId twice', async () => {
      const dto = { ...SAMPLE_REPO_DTO, githubRepoId: `upsert-${Date.now()}` }

      await request(app.getHttpServer())
        .post('/repos')
        .set('Cookie', sessionCookie)
        .send(dto)
        .expect(201)

      return request(app.getHttpServer())
        .post('/repos')
        .set('Cookie', sessionCookie)
        .send(dto)
        .expect(200)
    })
  })

  describe('GET /repos/:id', () => {
    let createdRepoId: string

    beforeAll(async () => {
      const dto = { ...SAMPLE_REPO_DTO, githubRepoId: `get-single-${Date.now()}` }
      const res = await request(app.getHttpServer())
        .post('/repos')
        .set('Cookie', sessionCookie)
        .send(dto)
      createdRepoId = res.body.id
    })

    it('returns 401 without auth session', () => {
      return request(app.getHttpServer()).get(`/repos/${createdRepoId}`).expect(401)
    })

    it('returns 200 with repo belonging to authenticated user', () => {
      return request(app.getHttpServer())
        .get(`/repos/${createdRepoId}`)
        .set('Cookie', sessionCookie)
        .expect(200)
        .expect((res) => {
          expect(res.body.id).toBe(createdRepoId)
        })
    })

    it('returns 404 for non-existent repo id', () => {
      return request(app.getHttpServer())
        .get('/repos/00000000-0000-0000-0000-000000000000')
        .set('Cookie', sessionCookie)
        .expect(404)
    })
  })

  describe('GET /repos/:id/analyses', () => {
    let createdRepoId: string

    beforeAll(async () => {
      const dto = { ...SAMPLE_REPO_DTO, githubRepoId: `analyses-list-${Date.now()}` }
      const res = await request(app.getHttpServer())
        .post('/repos')
        .set('Cookie', sessionCookie)
        .send(dto)
      createdRepoId = res.body.id
    })

    it('returns 401 without auth session', () => {
      return request(app.getHttpServer()).get(`/repos/${createdRepoId}/analyses`).expect(401)
    })

    it('returns 200 with empty array when no analyses exist', () => {
      return request(app.getHttpServer())
        .get(`/repos/${createdRepoId}/analyses`)
        .set('Cookie', sessionCookie)
        .expect(200)
        .expect((res) => {
          expect(Array.isArray(res.body)).toBe(true)
          expect(res.body).toHaveLength(0)
        })
    })
  })
})
