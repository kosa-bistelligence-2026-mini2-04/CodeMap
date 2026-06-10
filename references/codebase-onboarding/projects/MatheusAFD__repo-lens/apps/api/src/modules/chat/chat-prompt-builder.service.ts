import { Injectable } from '@nestjs/common'
import type { AnalysisResult, CodeArea } from '@repo/shared'

interface RepoMeta {
  owner: string
  name: string
  language: string | null
  description: string | null
}

interface FileChunk {
  path: string
  content: string
}

@Injectable()
export class ChatPromptBuilderService {
  buildSystemPrompt(
    repo: RepoMeta,
    hasAnalysis: boolean,
    hasFiles: boolean,
    areas: CodeArea[],
  ): string {
    const lines: string[] = []
    lines.push(
      `You are an expert software engineer answering questions about the repository ${repo.owner}/${repo.name} (primary language: ${repo.language ?? 'unknown'}).`,
    )
    lines.push('Be conversational, concise, and technically precise. Use GitHub-flavored markdown:')
    lines.push('- Use fenced code blocks with language hints for code snippets.')
    lines.push('- Cite repository file paths in inline backticks (e.g. `apps/api/src/main.ts`).')
    lines.push('- Use lists, tables, and headings (h3 max) only when they aid readability.')

    if (hasAnalysis) {
      lines.push(
        'A previous structured analysis of this repository is provided as JSON in the user bootstrap message. Use it as background but do NOT reproduce the JSON itself in your answer.',
      )
    }
    if (hasFiles) {
      lines.push(
        'Selected source files from the repository are included verbatim. Treat them as ground truth over the analysis when they conflict.',
      )
    }
    if (areas.length > 0) {
      lines.push(`Detected code areas in this repository: ${areas.map((a) => a.label).join(', ')}.`)
    }

    lines.push(
      'If the user asks about something not present in the provided context, say so explicitly rather than guessing.',
    )

    return lines.join('\n')
  }

  buildBootstrap(
    repo: RepoMeta,
    files: FileChunk[],
    latestAnalysis: Partial<AnalysisResult> | null,
  ): string {
    const parts: string[] = []
    parts.push(`Repository: ${repo.owner}/${repo.name}`)
    parts.push(`Primary language: ${repo.language ?? 'unknown'}`)
    if (repo.description) parts.push(`Description: ${repo.description}`)

    if (latestAnalysis) {
      const analysisJson = JSON.stringify(latestAnalysis).slice(0, 6000)
      parts.push('\n--- LATEST ANALYSIS (truncated JSON) ---')
      parts.push(analysisJson)
      parts.push('--- END ANALYSIS ---')
    }

    if (files.length > 0) {
      parts.push('\n--- SELECTED FILES ---')
      for (const file of files) {
        parts.push(`\n=== ${file.path} ===`)
        parts.push(file.content)
      }
      parts.push('--- END FILES ---')
    }

    return parts.join('\n')
  }
}
