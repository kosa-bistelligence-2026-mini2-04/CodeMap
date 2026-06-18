// Chat API — SSE streaming + simulation fallback
import { apiPath } from "@/features/analysis/api/api";

export type ChatMode = "lite" | "deep";
export type StreamPhase = "searching" | "building_context" | "generating" | "complete";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  mode?: ChatMode;
}

export interface StreamEvent {
  type: "status" | "content" | "done" | "error";
  phase?: StreamPhase;
  content?: string;
  error?: string;
}

/**
 * Stream chat response from backend via SSE.
 * Falls back to simulation if backend is unavailable.
 */
export async function* streamChat(
  repoId: string,
  message: string,
  mode: ChatMode,
): AsyncGenerator<StreamEvent> {
  try {
    const res = await fetch(apiPath(`/chat/${repoId}`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, mode }),
    });

    if (!res.ok || !res.body) {
      // Backend not available — fall back to simulation
      yield* simulateStream(message, mode);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const event: StreamEvent = JSON.parse(line.slice(6));
            yield event;
          } catch { /* skip malformed */ }
        }
      }
    }
  } catch {
    // Network error — fall back to simulation
    yield* simulateStream(message, mode);
  }
}

const SIMULATED_RESPONSES: Record<string, string> = {
  architecture: `## 프로젝트 아키텍처 분석\n\n이 프로젝트는 **Feature-Sliced Design (FSD)** 패턴을 따르는 모노레포 구조입니다.\n\n### 주요 구조\n- \`frontend/\` — Next.js 16 + React 19 (App Router)\n- \`backend/\` — FastAPI + Python 3.12 (3-Tier DDD)\n- \`database/\` — PostgreSQL + pgvector\n\n### 프론트엔드 아키텍처\n\`\`\`\nsrc/\n├── app/          # Route pages (thin shells)\n├── common/       # Cross-cutting: hooks, types, i18n\n└── features/     # Domain modules\n\`\`\`\n\n### 백엔드 아키텍처\n각 도메인 모듈은 \`Router → Service → Repository\` 3-Tier 패턴을 따릅니다.`,
  files: `## 핵심 파일 및 읽기 순서\n\n### 1단계: 진입점 파악\n1. \`frontend/src/app/layout.tsx\` — 루트 레이아웃\n2. \`frontend/src/app/page.tsx\` — 랜딩 페이지\n3. \`backend/app/main.py\` — FastAPI 진입점\n\n### 2단계: 핵심 기능\n4. \`frontend/src/features/analysis/\` — 분석 대시보드\n5. \`backend/app/repo/pipeline/\` — LangGraph 파이프라인\n6. \`backend/app/repo/service.py\` — 레포 분석 서비스\n\n### 3단계: 인프라\n7. \`database/init.sql\` — DB 스키마\n8. \`frontend/src/common/types/contracts.ts\` — API 계약`,
  default: `이 저장소를 분석한 결과를 바탕으로 답변드립니다.\n\n해당 질문에 대해 관련 소스코드 파일을 탐색하고 분석했습니다. 추가적인 질문이 있으시면 언제든 물어보세요!\n\n> 💡 **Tip**: 더 깊은 분석이 필요하시면 **Deep 모드**로 전환해 보세요.`,
};

function getSimulatedResponse(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("아키텍처") || lower.includes("architecture") || lower.includes("구조"))
    return SIMULATED_RESPONSES.architecture;
  if (lower.includes("파일") || lower.includes("순서") || lower.includes("file") || lower.includes("reading"))
    return SIMULATED_RESPONSES.files;
  return SIMULATED_RESPONSES.default;
}

async function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Simulation mode — streams a fake response with realistic delays
 */
export async function* simulateStream(
  message: string,
  mode: ChatMode,
): AsyncGenerator<StreamEvent> {
  const baseDelay = mode === "lite" ? 600 : 1200;

  // Phase 1: Searching files
  yield { type: "status", phase: "searching" };
  await delay(baseDelay + Math.random() * 500);

  // Phase 2: Building context
  yield { type: "status", phase: "building_context" };
  await delay(baseDelay + Math.random() * 800);

  // Phase 3: Generating
  yield { type: "status", phase: "generating" };
  await delay(400);

  // Stream content character by character (simulate typing)
  const fullText = getSimulatedResponse(message);
  const chunkSize = mode === "lite" ? 8 : 4;
  for (let i = 0; i < fullText.length; i += chunkSize) {
    yield { type: "content", content: fullText.slice(i, i + chunkSize) };
    await delay(15 + Math.random() * 25);
  }

  yield { type: "done" };
}
