interface MockChunk {
  type: string
  delta?: { type: string; text: string }
  message?: { usage?: { input_tokens: number } }
  usage?: { output_tokens: number }
}

const MOCK_DELTAS = [
  '## Mocked response\n\n',
  'This is a **mock streaming response** generated because `ANTHROPIC_MOCK=true`.\n\n',
  '- It pretends to call Anthropic.\n',
  '- It splits into a few deltas.\n',
  '- It exits cleanly.\n\n',
  'Try real mode by unsetting `ANTHROPIC_MOCK`.\n',
]

export async function* createMockChatStream(): AsyncGenerator<MockChunk> {
  yield { type: 'message_start', message: { usage: { input_tokens: 42 } } }

  for (const text of MOCK_DELTAS) {
    await new Promise((resolve) => setTimeout(resolve, 50))
    yield {
      type: 'content_block_delta',
      delta: { type: 'text_delta', text },
    }
  }

  yield { type: 'message_delta', usage: { output_tokens: 84 } }
}
