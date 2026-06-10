import { UnauthorizedException } from '@nestjs/common'
import { Test, type TestingModule } from '@nestjs/testing'

jest.mock('@thallesp/nestjs-better-auth', () => ({
  AllowAnonymous: () => () => {},
  Roles: () => () => {},
  Session: () => () => {},
}))

jest.mock('../../config/database', () => ({
  db: {
    select: jest.fn(),
  },
}))

import { db } from '../../config/database'
import { GithubService } from './github.service'
import { GetFileContentUseCase } from './use-cases/get-file-content.use-case'
import { GetRepoTreeUseCase } from './use-cases/get-repo-tree.use-case'
import { GetTokenUseCase } from './use-cases/get-token.use-case'
import { ListUserReposUseCase } from './use-cases/list-user-repos.use-case'

const mockDb = db as jest.Mocked<typeof db>

describe('GithubService', () => {
  let service: GithubService

  beforeEach(async () => {
    jest.clearAllMocks()
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        GithubService,
        GetTokenUseCase,
        ListUserReposUseCase,
        GetRepoTreeUseCase,
        GetFileContentUseCase,
      ],
    }).compile()
    service = module.get<GithubService>(GithubService)
  })

  describe('getToken', () => {
    it('returns accessToken when github account exists for userId', async () => {
      const mockSelect = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockResolvedValue([{ accessToken: 'ghp_test_token' }]),
        }),
      })
      mockDb.select = mockSelect

      const result = await service.getToken('user-123')

      expect(result).toBe('ghp_test_token')
    })

    it('returns null when no github account exists for userId', async () => {
      const mockSelect = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockResolvedValue([]),
        }),
      })
      mockDb.select = mockSelect

      const result = await service.getToken('user-no-github')

      expect(result).toBeNull()
    })
  })

  describe('listUserRepos', () => {
    it('returns [UnauthorizedException, null] when no github token found', async () => {
      const mockSelect = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockResolvedValue([]),
        }),
      })
      mockDb.select = mockSelect

      const [error, data] = await service.listUserRepos('user-no-token')

      expect(error).toBeInstanceOf(UnauthorizedException)
      expect(data).toBeNull()
    })

    it('returns [Error, null] when GitHub API returns non-ok status', async () => {
      const mockSelect = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockResolvedValue([{ accessToken: 'ghp_token' }]),
        }),
      })
      mockDb.select = mockSelect

      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 401,
      } as Response)

      const [error, data] = await service.listUserRepos('user-123')

      expect(error).toBeInstanceOf(Error)
      expect((error as Error).message).toMatch(/401/)
      expect(data).toBeNull()
    })

    it('returns [null, repos] when GitHub API returns ok', async () => {
      const mockRepos = [{ id: 1, name: 'my-repo', full_name: 'owner/my-repo' }]
      const mockSelect = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockResolvedValue([{ accessToken: 'ghp_token' }]),
        }),
      })
      mockDb.select = mockSelect

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockRepos),
      } as unknown as Response)

      const [error, data] = await service.listUserRepos('user-123')

      expect(error).toBeNull()
      expect(data).toEqual(mockRepos)
    })

    it('returns [Error, null] when GitHub API returns 403 for the stored token', async () => {
      const mockSelect = jest.fn().mockReturnValue({
        from: jest.fn().mockReturnValue({
          where: jest.fn().mockResolvedValue([{ accessToken: 'ghp_revoked_token' }]),
        }),
      })
      mockDb.select = mockSelect

      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 403,
      } as Response)

      const [error, data] = await service.listUserRepos('user-123')

      expect(error).toBeInstanceOf(Error)
      expect(data).toBeNull()
    })
  })

  describe('getRepoTree', () => {
    it('returns [Error, null] when GitHub API returns non-ok status', async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
      } as Response)

      const [error, data] = await service.getRepoTree('owner', 'repo', 'ghp_token')

      expect(error).toBeInstanceOf(Error)
      expect(data).toBeNull()
    })

    it('returns [null, tree items] when GitHub API returns ok', async () => {
      const mockTree = [
        { path: 'src/index.ts', type: 'blob', sha: 'abc123' },
        { path: 'src/', type: 'tree', sha: 'def456' },
      ]

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ tree: mockTree, truncated: false }),
      } as unknown as Response)

      const [error, data] = await service.getRepoTree('owner', 'repo', 'ghp_token')

      expect(error).toBeNull()
      expect(data).toEqual(mockTree)
    })
  })

  describe('getFileContent', () => {
    it('returns [Error, null] when response is not ok', async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
      } as Response)

      const [error, data] = await service.getFileContent(
        'owner',
        'repo',
        'src/index.ts',
        'ghp_token',
      )

      expect(error).toBeInstanceOf(Error)
      expect(data).toBeNull()
    })

    it('returns [Error, null] when response encoding is not base64', async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ content: 'hello', encoding: 'utf-8' }),
      } as unknown as Response)

      const [error, data] = await service.getFileContent(
        'owner',
        'repo',
        'src/index.ts',
        'ghp_token',
      )

      expect(error).toBeInstanceOf(Error)
      expect((error as Error).message).toMatch(/Unexpected response format/)
      expect(data).toBeNull()
    })

    it('returns [null, decoded string] for valid base64 content', async () => {
      const original = 'export const hello = "world"'
      const encoded = Buffer.from(original).toString('base64')

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ content: encoded, encoding: 'base64' }),
      } as unknown as Response)

      const [error, data] = await service.getFileContent(
        'owner',
        'repo',
        'src/index.ts',
        'ghp_token',
      )

      expect(error).toBeNull()
      expect(data).toBe(original)
    })
  })
})
