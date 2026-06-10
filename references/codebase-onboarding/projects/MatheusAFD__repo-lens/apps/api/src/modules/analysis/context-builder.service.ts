import { Injectable } from '@nestjs/common'
import { GithubService, type GithubTreeItem } from '../github/github.service'

const MANIFEST_SCORE: Record<string, number> = {
  'package.json': 100,
  'go.mod': 100,
  'Cargo.toml': 100,
  'pom.xml': 100,
  'requirements.txt': 100,
  'pyproject.toml': 100,
  Gemfile: 100,
  'composer.json': 100,
  'build.gradle': 100,
  'build.gradle.kts': 100,
  'README.md': 90,
  'readme.md': 90,
  Dockerfile: 85,
  'docker-compose.yml': 85,
  'docker-compose.yaml': 85,
  'tsconfig.json': 70,
  'biome.json': 60,
  '.eslintrc.json': 60,
  '.eslintrc.js': 60,
}

const EXCLUDED_FILES = new Set([
  'package-lock.json',
  'yarn.lock',
  'pnpm-lock.yaml',
  'Cargo.lock',
  'poetry.lock',
  'Gemfile.lock',
  'go.sum',
])

const EXTENSION_SCORE: Record<string, number> = {
  '.ts': 40,
  '.tsx': 40,
  '.go': 40,
  '.rs': 40,
  '.py': 40,
  '.java': 40,
  '.cs': 40,
  '.rb': 40,
  '.js': 30,
  '.jsx': 30,
  '.php': 30,
  '.json': 20,
  '.yaml': 20,
  '.yml': 20,
  '.toml': 20,
  '.md': 15,
  '.css': 5,
  '.scss': 5,
  '.html': 5,
}

const EXCLUDED_EXTENSIONS = new Set([
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.svg',
  '.ico',
  '.woff',
  '.woff2',
  '.ttf',
  '.eot',
  '.lock',
  '.sum',
])

const TOKEN_CHAR_BUDGET = 40_000

interface FileWithContent {
  path: string
  content: string
}

@Injectable()
export class ContextBuilderService {
  async buildContext(
    owner: string,
    repo: string,
    tree: GithubTreeItem[],
    githubService: GithubService,
    token: string,
  ): Promise<FileWithContent[]> {
    const scored = this.scoreFiles(tree)
    const selected = this.selectFiles(scored)
    const files: FileWithContent[] = []
    let budget = TOKEN_CHAR_BUDGET

    for (const item of selected) {
      if (budget <= 0) break

      const [fetchError, content] = await githubService.getFileContent(
        owner,
        repo,
        item.path,
        token,
      )
      if (fetchError || !content) continue

      const lines = content.split('\n')

      const truncated =
        lines.length > 150 ? `${lines.slice(0, 150).join('\n')}\n... (truncated)` : content

      files.push({ path: item.path, content: truncated })
      budget -= truncated.length
    }

    return files
  }

  private scoreFiles(tree: GithubTreeItem[]): { path: string; score: number }[] {
    return tree
      .filter((item) => item.type === 'blob')
      .map((item) => ({ path: item.path, score: this.score(item) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score)
  }

  private score(item: GithubTreeItem): number {
    const basename = item.path.split('/').pop() ?? ''
    const ext = basename.includes('.') ? `.${basename.split('.').pop()}` : ''

    if (EXCLUDED_FILES.has(basename)) return -1
    if (EXCLUDED_EXTENSIONS.has(ext.toLowerCase())) return -1
    if (basename.startsWith('.') && !MANIFEST_SCORE[basename]) return 0

    if (/\/(test|tests|__tests__|spec|__mocks__|fixtures|e2e)\//.test(item.path)) return 5

    let fileScore = 0

    if (MANIFEST_SCORE[basename] !== undefined) {
      fileScore = MANIFEST_SCORE[basename]
    } else if (item.path.startsWith('.github/workflows/')) {
      fileScore = 80
    } else {
      fileScore = EXTENSION_SCORE[ext.toLowerCase()] ?? 0
    }

    const depth = item.path.split('/').length - 1
    if (depth > 3) fileScore -= (depth - 3) * 8

    if (/(^|\/)node_modules\//.test(item.path)) return -1
    if (/\/(vendor|dist|build|\.next|\.turbo|coverage)\//.test(item.path)) return -1

    return Math.max(fileScore, 0)
  }

  private selectFiles(
    scored: { path: string; score: number }[],
  ): { path: string; score: number }[] {
    const priority = scored.filter((file) => file.score >= 80)
    const rest = scored.filter((file) => file.score < 80)
    return [...priority, ...rest].slice(0, 60)
  }
}
