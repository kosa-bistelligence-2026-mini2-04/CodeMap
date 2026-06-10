import { Test, type TestingModule } from '@nestjs/testing'

jest.mock('@thallesp/nestjs-better-auth', () => ({
  AllowAnonymous: () => () => {},
}))

import { PromptBuilderService } from './prompt-builder.service'

describe('PromptBuilderService', () => {
  let service: PromptBuilderService

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [PromptBuilderService],
    }).compile()
    service = module.get<PromptBuilderService>(PromptBuilderService)
  })

  describe('buildSystemPrompt', () => {
    it('contains all requested section names', () => {
      const sections = [
        'executive_summary',
        'tech_stack',
        'architecture',
        'security',
        'dependencies',
        'update_plan',
        'recommendations',
      ] as const
      const prompt = service.buildSystemPrompt([...sections], false)

      for (const section of sections) {
        expect(prompt).toContain(section)
      }
    })

    it('contains BEGIN_SECTION and END_SECTION marker patterns', () => {
      const prompt = service.buildSystemPrompt(['executive_summary', 'security'], false)

      expect(prompt).toContain('##BEGIN_SECTION:')
      expect(prompt).toContain('##END_SECTION:')
    })

    it('only includes requested sections — omits others', () => {
      const prompt = service.buildSystemPrompt(['executive_summary', 'security'], false)

      expect(prompt).toContain('executive_summary')
      expect(prompt).toContain('security')
      expect(prompt).not.toContain('tech_stack')
      expect(prompt).not.toContain('dependencies')
    })

    it('mentions correct section count', () => {
      const prompt = service.buildSystemPrompt(['executive_summary', 'security'], false)

      expect(prompt).toContain('2')
    })

    it('includes code_metrics shape when requested', () => {
      const prompt = service.buildSystemPrompt(['code_metrics'], false)

      expect(prompt).toContain('code_metrics')
      expect(prompt).toContain('totalFiles')
      expect(prompt).toContain('estimatedLines')
      expect(prompt).toContain('largestFiles')
    })

    it('includes fun_facts shape when requested', () => {
      const prompt = service.buildSystemPrompt(['fun_facts'], false)

      expect(prompt).toContain('fun_facts')
      expect(prompt).toContain('facts')
      expect(prompt).toContain('codeAge')
    })
  })

  describe('buildUserPrompt', () => {
    const files = [
      { path: 'src/index.ts', content: 'export const app = 1' },
      { path: 'package.json', content: '{"name":"test"}' },
    ]

    it('includes repository owner/name header', () => {
      const prompt = service.buildUserPrompt(
        { owner: 'acme', name: 'my-app', language: 'TypeScript', description: null },
        files,
      )

      expect(prompt).toContain('Repository: acme/my-app')
    })

    it('includes primary language', () => {
      const prompt = service.buildUserPrompt(
        { owner: 'acme', name: 'my-app', language: 'TypeScript', description: null },
        files,
      )

      expect(prompt).toContain('Primary Language: TypeScript')
    })

    it('uses "Unknown" when language is null', () => {
      const prompt = service.buildUserPrompt(
        { owner: 'acme', name: 'my-app', language: null, description: null },
        files,
      )

      expect(prompt).toContain('Primary Language: Unknown')
    })

    it('uses "No description provided" when description is null', () => {
      const prompt = service.buildUserPrompt(
        { owner: 'acme', name: 'my-app', language: 'TypeScript', description: null },
        files,
      )

      expect(prompt).toContain('Description: No description provided')
    })

    it('includes file path headers with === delimiters', () => {
      const prompt = service.buildUserPrompt(
        { owner: 'acme', name: 'my-app', language: 'TypeScript', description: null },
        files,
      )

      expect(prompt).toContain('=== src/index.ts ===')
      expect(prompt).toContain('=== package.json ===')
    })

    it('includes file contents', () => {
      const prompt = service.buildUserPrompt(
        { owner: 'acme', name: 'my-app', language: 'TypeScript', description: null },
        files,
      )

      expect(prompt).toContain('export const app = 1')
      expect(prompt).toContain('{"name":"test"}')
    })

    it('includes description when provided', () => {
      const prompt = service.buildUserPrompt(
        { owner: 'acme', name: 'my-app', language: 'TypeScript', description: 'A cool app' },
        files,
      )

      expect(prompt).toContain('Description: A cool app')
    })

    it('includes customContext when provided', () => {
      const prompt = service.buildUserPrompt(
        { owner: 'acme', name: 'my-app', language: 'TypeScript', description: null },
        files,
        'This is a B2B SaaS focused on LGPD compliance',
      )

      expect(prompt).toContain('This is a B2B SaaS focused on LGPD compliance')
    })

    it('does not include customContext section when not provided', () => {
      const prompt = service.buildUserPrompt(
        { owner: 'acme', name: 'my-app', language: 'TypeScript', description: null },
        files,
      )

      expect(prompt).not.toContain('Additional context from the user')
    })
  })
})
