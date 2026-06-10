type ChunkType =
  | { type: 'message_start'; message: { usage: { input_tokens: number } } }
  | { type: 'content_block_delta'; delta: { type: 'text_delta'; text: string } }
  | { type: 'message_delta'; usage: { output_tokens: number } }

const MOCK_RESULT_SECTIONS = [
  {
    name: 'executive_summary',
    data: {
      summary: 'A well-structured TypeScript application with clean architecture.',
      targetAudience: 'Developers and technical teams',
      keyCapabilities: ['REST API', 'Authentication', 'Data persistence'],
    },
  },
  {
    name: 'tech_stack',
    data: {
      languages: [
        { name: 'TypeScript', percentage: 85 },
        { name: 'SQL', percentage: 15 },
      ],
      frameworks: ['NestJS', 'React'],
      databases: ['PostgreSQL'],
      cloud: [],
      testing: ['Jest', 'Playwright'],
    },
  },
  {
    name: 'architecture',
    data: {
      pattern: 'Monorepo',
      description: 'Modular monorepo with shared packages.',
      keyPatterns: ['Module per feature', 'Shared type definitions'],
      observations: ['Clear separation of concerns', 'Reusable UI components'],
    },
  },
  {
    name: 'security',
    data: {
      grade: 'B',
      score: 78,
      findings: [],
      positives: ['Uses parameterized queries', 'Proper CORS configuration'],
    },
  },
  {
    name: 'dependencies',
    data: {
      total: 20,
      ecosystems: [{ name: 'npm', count: 20, outdated: 2, vulnerable: 0 }],
      highlights: [
        { name: 'drizzle-orm', version: '0.42.0', latestVersion: '0.45.0', status: 'outdated' },
      ],
    },
  },
  {
    name: 'update_plan',
    data: {
      critical: [],
      major: [
        {
          name: 'drizzle-orm',
          current: '0.42.0',
          target: '0.45.0',
          reason: 'New features and bug fixes',
          gain: 'Improved query performance',
        },
      ],
      minor: [],
    },
  },
  {
    name: 'recommendations',
    data: {
      items: [
        {
          rank: 1,
          title: 'Add integration tests',
          impact: 'high',
          effort: 'medium',
          rationale: 'Improves confidence in critical paths',
        },
        {
          rank: 2,
          title: 'Add input validation',
          impact: 'medium',
          effort: 'low',
          rationale: 'Protects against invalid data entering the system',
        },
      ],
    },
  },
  {
    name: 'code_metrics',
    data: {
      totalFiles: 42,
      estimatedLines: 3200,
      byLanguage: [
        { name: 'TypeScript', lines: 2800, percentage: 87 },
        { name: 'SQL', lines: 400, percentage: 13 },
      ],
      largestFiles: [
        { path: 'apps/api/src/modules/analysis/analysis.service.ts', lines: 280 },
        { path: 'apps/portal/src/modules/analysis/components/analysis-page.tsx', lines: 360 },
      ],
    },
  },
  {
    name: 'fun_facts',
    data: {
      facts: [
        'The project has over 40 TypeScript files.',
        'It uses a monorepo structure with shared packages.',
        'The API is built with NestJS and uses Drizzle ORM for type-safe queries.',
        'Authentication is handled via Better Auth with GitHub OAuth.',
        'The frontend uses TanStack Start with server-side rendering.',
      ],
      codeAge: null,
    },
  },
]

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

async function* buildMockStream(sections: string[]): AsyncGenerator<ChunkType> {
  await delay(300)

  yield {
    type: 'message_start',
    message: { usage: { input_tokens: 1000 } },
  }

  const filtered =
    sections.length > 0
      ? MOCK_RESULT_SECTIONS.filter((s) => sections.includes(s.name))
      : MOCK_RESULT_SECTIONS

  for (const section of filtered) {
    const text = `##BEGIN_SECTION:${section.name}##\n${JSON.stringify(section.data)}\n##END_SECTION:${section.name}##\n`

    yield {
      type: 'content_block_delta',
      delta: { type: 'text_delta', text },
    }
  }

  yield {
    type: 'message_delta',
    usage: { output_tokens: 500 },
  }
}

export function createMockAnthropicStream(sections: string[] = []) {
  return buildMockStream(sections)
}
