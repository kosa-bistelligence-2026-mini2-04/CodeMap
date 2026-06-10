import { NotFoundException } from '@nestjs/common'
import { Test, type TestingModule } from '@nestjs/testing'

jest.mock('@thallesp/nestjs-better-auth', () => ({
  AllowAnonymous: () => () => {},
  Roles: () => () => {},
  Session: () => () => {},
}))

jest.mock('../../config/database', () => ({
  db: {
    select: jest.fn(),
    insert: jest.fn(),
    update: jest.fn(),
  },
}))

import { db } from '../../config/database'
import { ReposService } from './repos.service'
import { GetRepoUseCase } from './use-cases/get-repo.use-case'
import { ListAnalysesUseCase } from './use-cases/list-analyses.use-case'
import { ListReposUseCase } from './use-cases/list-repos.use-case'
import { UpsertRepoUseCase } from './use-cases/upsert-repo.use-case'

const mockDb = db as jest.Mocked<typeof db>

describe('ReposService', () => {
  let service: ReposService

  beforeEach(async () => {
    jest.clearAllMocks()
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        ReposService,
        ListReposUseCase,
        UpsertRepoUseCase,
        GetRepoUseCase,
        ListAnalysesUseCase,
      ],
    }).compile()
    service = module.get<ReposService>(ReposService)
  })

  describe('listRepos', () => {
    it('returns empty array when no repos exist for userId', async () => {
      mockDb.select = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          leftJoin: jest.fn().mockReturnValue({
            where: jest.fn().mockReturnValue({
              groupBy: jest.fn().mockReturnValue({
                orderBy: jest.fn().mockResolvedValue([]),
              }),
            }),
          }),
        }),
      })

      const result = await service.listRepos('user-no-repos')
      expect(result).toEqual([])
    })

    it('sets hasAnalysis: false when lastAnalyzedAt is null', async () => {
      const mockRow = {
        id: 'repo-1',
        userId: 'user-1',
        githubRepoId: '111',
        owner: 'owner',
        name: 'repo',
        fullName: 'owner/repo',
        description: null,
        language: 'TypeScript',
        isPrivate: false,
        htmlUrl: 'https://github.com/owner/repo',
        createdAt: new Date(),
        updatedAt: new Date(),
        lastAnalyzedAt: null,
      }

      mockDb.select = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          leftJoin: jest.fn().mockReturnValue({
            where: jest.fn().mockReturnValue({
              groupBy: jest.fn().mockReturnValue({
                orderBy: jest.fn().mockResolvedValue([mockRow]),
              }),
            }),
          }),
        }),
      })

      const result = await service.listRepos('user-1')

      expect(result[0].hasAnalysis).toBe(false)
      expect(result[0].lastAnalyzedAt).toBeNull()
    })

    it('sets hasAnalysis: true when lastAnalyzedAt is set', async () => {
      const mockRow = {
        id: 'repo-1',
        userId: 'user-1',
        githubRepoId: '111',
        owner: 'owner',
        name: 'repo',
        fullName: 'owner/repo',
        description: null,
        language: 'TypeScript',
        isPrivate: false,
        htmlUrl: 'https://github.com/owner/repo',
        createdAt: new Date(),
        updatedAt: new Date(),
        lastAnalyzedAt: new Date().toISOString(),
      }

      mockDb.select = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          leftJoin: jest.fn().mockReturnValue({
            where: jest.fn().mockReturnValue({
              groupBy: jest.fn().mockReturnValue({
                orderBy: jest.fn().mockResolvedValue([mockRow]),
              }),
            }),
          }),
        }),
      })

      const result = await service.listRepos('user-1')

      expect(result[0].hasAnalysis).toBe(true)
    })
  })

  describe('getRepo', () => {
    it('returns [NotFoundException, null] when repo not found', async () => {
      mockDb.select = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockResolvedValue([]),
        }),
      })

      const [error, data] = await service.getRepo('non-existent', 'user-1')

      expect(error).toBeInstanceOf(NotFoundException)
      expect(data).toBeNull()
    })

    it('returns [null, repo] when repo belongs to user', async () => {
      const mockRepo = {
        id: 'repo-1',
        userId: 'user-1',
        name: 'test-repo',
      }

      mockDb.select = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockResolvedValue([mockRepo]),
        }),
      })

      const [error, data] = await service.getRepo('repo-1', 'user-1')

      expect(error).toBeNull()
      expect(data).toEqual(mockRepo)
    })
  })

  describe('listAnalyses', () => {
    it('extracts securityGrade from result JSON when present', async () => {
      const resultJson = JSON.stringify({ security: { grade: 'A' } })

      mockDb.select = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockReturnValue({
            orderBy: jest.fn().mockResolvedValue([
              {
                id: 'analysis-1',
                status: 'completed',
                createdAt: new Date(),
                completedAt: new Date(),
                inputTokens: 100,
                outputTokens: 200,
                result: resultJson,
              },
            ]),
          }),
        }),
      })

      const result = await service.listAnalyses('repo-1', 'user-1')

      expect(result[0].securityGrade).toBe('A')
    })

    it('returns null securityGrade when result is null', async () => {
      mockDb.select = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockReturnValue({
            orderBy: jest.fn().mockResolvedValue([
              {
                id: 'analysis-1',
                status: 'running',
                createdAt: new Date(),
                completedAt: null,
                inputTokens: null,
                outputTokens: null,
                result: null,
              },
            ]),
          }),
        }),
      })

      const result = await service.listAnalyses('repo-1', 'user-1')

      expect(result[0].securityGrade).toBeNull()
    })

    it('returns null securityGrade when result JSON is malformed', async () => {
      mockDb.select = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockReturnValue({
            orderBy: jest.fn().mockResolvedValue([
              {
                id: 'analysis-1',
                status: 'completed',
                createdAt: new Date(),
                completedAt: new Date(),
                inputTokens: 100,
                outputTokens: 200,
                result: 'not-valid-json{{{',
              },
            ]),
          }),
        }),
      })

      const result = await service.listAnalyses('repo-1', 'user-1')

      expect(result[0].securityGrade).toBeNull()
    })
  })
})
