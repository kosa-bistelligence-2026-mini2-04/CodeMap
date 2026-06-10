interface ParsedSection {
  name: string
  data: unknown
}

interface ParseResult {
  sections: ParsedSection[]
  remaining: string
}

const BEGIN_PATTERN = /##BEGIN_SECTION:(\w+)##/

export function parseSections(buffer: string): ParseResult {
  let remaining = buffer
  const sections: ParsedSection[] = []

  while (true) {
    const beginMatch = remaining.match(BEGIN_PATTERN)
    if (!beginMatch) break

    const sectionName = beginMatch[1]
    const afterBegin = remaining.slice((beginMatch.index ?? 0) + beginMatch[0].length)

    const endMatch = afterBegin.match(new RegExp(`##END_SECTION:${sectionName}##`))
    if (!endMatch) break

    const jsonStr = afterBegin.slice(0, endMatch.index).trim()

    try {
      const data = JSON.parse(jsonStr)
      sections.push({ name: sectionName, data })
    } catch {}

    remaining = afterBegin.slice((endMatch.index ?? 0) + endMatch[0].length)
  }

  return { sections, remaining }
}
