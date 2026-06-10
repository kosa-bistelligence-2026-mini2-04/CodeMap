import { Test, type TestingModule } from '@nestjs/testing'

jest.mock('@thallesp/nestjs-better-auth', () => ({
  AllowAnonymous: () => () => {},
}))

import { ContextBuilderService } from './context-builder.service'
import type { GithubService, GithubTreeItem } from '../github/github.service'

type MockGithubService = Pick<GithubService, 'getFileContent'>

function makeBlob(path: string, size = 100): GithubTreeItem {
  return { path, type: 'blob', size, sha: 'abc' }
}

function mockGithub(impl: jest.MockedFunction<GithubService['getFileContent']>): MockGithubService {
  return { getFileContent: impl }
}

describe('ContextBuilderService', () => {
  let service: ContextBuilderService

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [ContextBuilderService],
    }).compile()
    service = module.get<ContextBuilderService>(ContextBuilderService)
  })

  describe('buildContext', () => {
    it('returns empty array when tree has no blobs', async () => {
      const tree: GithubTreeItem[] = [{ path: 'src/', type: 'tree', sha: 'abc' }]
      const getFileContent = jest.fn() as jest.MockedFunction<GithubService['getFileContent']>
      const github = mockGithub(getFileContent)

      const result = await service.buildContext(
        'owner',
        'repo',
        tree,
        github as GithubService,
        'token',
      )

      expect(result).toEqual([])
      expect(getFileContent).not.toHaveBeenCalled()
    })

    it('skips files where getFileContent returns an error', async () => {
      const tree = [makeBlob('src/index.ts')]
      const getFileContent = jest
        .fn()
        .mockResolvedValue([new Error('Not found'), null]) as jest.MockedFunction<
        GithubService['getFileContent']
      >

      const result = await service.buildContext(
        'owner',
        'repo',
        tree,
        mockGithub(getFileContent) as GithubService,
        'token',
      )

      expect(result).toEqual([])
    })

    it('truncates files longer than 150 lines to at most 152 lines', async () => {
      const tree = [makeBlob('src/big.ts')]
      const longContent = Array.from({ length: 200 }, (_, i) => `line ${i}`).join('\n')
      const getFileContent = jest
        .fn()
        .mockResolvedValue([null, longContent]) as jest.MockedFunction<
        GithubService['getFileContent']
      >

      const result = await service.buildContext(
        'owner',
        'repo',
        tree,
        mockGithub(getFileContent) as GithubService,
        'token',
      )

      const lineCount = result[0].content.split('\n').length
      expect(lineCount).toBeLessThanOrEqual(152)
      expect(lineCount).toBeLessThan(200)
    })

    it('respects token char budget and stops fetching after budget exhausted', async () => {
      const tree = [makeBlob('src/a.ts'), makeBlob('src/b.ts'), makeBlob('src/c.ts')]
      const largeContent = 'x'.repeat(40_000)
      const getFileContent = jest
        .fn()
        .mockResolvedValue([null, largeContent]) as jest.MockedFunction<
        GithubService['getFileContent']
      >

      const result = await service.buildContext(
        'owner',
        'repo',
        tree,
        mockGithub(getFileContent) as GithubService,
        'token',
      )

      expect(result.length).toBe(1)
    })

    it('returns at most 60 files', async () => {
      const tree = Array.from({ length: 80 }, (_, i) => makeBlob(`src/file${i}.ts`))
      const getFileContent = jest
        .fn()
        .mockResolvedValue([null, 'short content']) as jest.MockedFunction<
        GithubService['getFileContent']
      >

      const result = await service.buildContext(
        'owner',
        'repo',
        tree,
        mockGithub(getFileContent) as GithubService,
        'token',
      )

      expect(result.length).toBeLessThanOrEqual(60)
    })
  })

  describe('file scoring', () => {
    it('assigns highest score to package.json', async () => {
      const tree = [makeBlob('package.json'), makeBlob('src/index.ts')]
      const getFileContent = jest.fn().mockResolvedValue([null, 'content']) as jest.MockedFunction<
        GithubService['getFileContent']
      >

      await service.buildContext(
        'owner',
        'repo',
        tree,
        mockGithub(getFileContent) as GithubService,
        'token',
      )

      const paths = getFileContent.mock.calls.map((c) => c[2])
      expect(paths[0]).toBe('package.json')
    })

    it('filters out pnpm-lock.yaml', async () => {
      const tree = [makeBlob('pnpm-lock.yaml'), makeBlob('src/index.ts')]
      const getFileContent = jest.fn().mockResolvedValue([null, 'content']) as jest.MockedFunction<
        GithubService['getFileContent']
      >

      await service.buildContext(
        'owner',
        'repo',
        tree,
        mockGithub(getFileContent) as GithubService,
        'token',
      )

      const paths = getFileContent.mock.calls.map((c) => c[2])
      expect(paths).not.toContain('pnpm-lock.yaml')
    })

    it('filters out binary extensions like .png', async () => {
      const tree = [makeBlob('logo.png'), makeBlob('src/index.ts')]
      const getFileContent = jest.fn().mockResolvedValue([null, 'content']) as jest.MockedFunction<
        GithubService['getFileContent']
      >

      await service.buildContext(
        'owner',
        'repo',
        tree,
        mockGithub(getFileContent) as GithubService,
        'token',
      )

      const paths = getFileContent.mock.calls.map((c) => c[2])
      expect(paths).not.toContain('logo.png')
    })

    it('filters out files in node_modules', async () => {
      const tree = [makeBlob('node_modules/lodash/index.js'), makeBlob('src/app.ts')]
      const getFileContent = jest.fn().mockResolvedValue([null, 'content']) as jest.MockedFunction<
        GithubService['getFileContent']
      >

      await service.buildContext(
        'owner',
        'repo',
        tree,
        mockGithub(getFileContent) as GithubService,
        'token',
      )

      const paths = getFileContent.mock.calls.map((c) => c[2])
      expect(paths).not.toContain('node_modules/lodash/index.js')
    })
  })
})
