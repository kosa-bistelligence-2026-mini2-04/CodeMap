import type { ChatMode, CodeReference, StreamPhase } from "@/common/types/contracts";
import { apiPath } from "@/features/analysis/api/api";

export type { ChatMode, StreamPhase };

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  mode?: ChatMode;
  explorationSteps?: string[];
  references?: CodeReference[];
  suggestions?: string[];
}

export interface StreamEvent {
  type: "status" | "content" | "done" | "error" | "exploration" | "references" | "thread" | "suggestions";
  phase?: StreamPhase;
  content?: string;
  error?: string;
  step?: string;
  references?: CodeReference[];
  threadId?: string;
  suggestions?: string[];
}

interface StreamChatOptions {
  threadId?: string | null;
  contextFile?: string | null;
}

export async function* streamChat(
  repoId: string,
  message: string,
  mode: ChatMode,
  options: StreamChatOptions = {},
): AsyncGenerator<StreamEvent> {
  let response: Response;
  try {
    response = await fetch(apiPath(`/chat/${repoId}`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        mode,
        threadId: options.threadId || undefined,
        contextFile: options.contextFile || undefined,
      }),
    });
  } catch {
    yield { type: "error", error: "채팅 서버에 연결할 수 없습니다. 백엔드 상태를 확인해주세요." };
    return;
  }

  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => null);
    yield {
      type: "error",
      error: payload?.detail || `채팅 요청에 실패했습니다. (${response.status})`,
    };
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        yield JSON.parse(line.slice(6)) as StreamEvent;
      } catch {
        yield { type: "error", error: "스트리밍 응답을 해석하지 못했습니다." };
      }
    }
  }
}

export async function fetchThread(repoId: string, threadId: string): Promise<ChatMessage[]> {
  const response = await fetch(apiPath(`/chat/${repoId}/threads/${threadId}`));
  if (!response.ok) return [];
  const payload = await response.json();
  return (payload.items || []).map((item: Record<string, unknown>) => ({
    id: String(item.id),
    role: item.role as "user" | "assistant",
    content: String(item.content || ""),
    timestamp: Date.parse(String(item.createdAt || new Date().toISOString())),
    mode: item.mode as ChatMode,
    references: (item.references || []) as CodeReference[],
  }));
}

const PREVIEW_ANSWERS: Record<string, string> = {
  architecture: "분석 결과를 보면 프런트엔드는 Next.js App Router, 백엔드는 FastAPI 도메인 모듈로 나뉩니다. `frontend/src/app`이 화면 진입점이고 `backend/app/repo`가 분석 파이프라인 경계입니다.",
  default: "현재 선택한 분석 근거를 바탕으로 답변을 준비했습니다. 실제 프로젝트에서는 서버가 저장소 스냅샷을 검색하고 파일·라인 출처와 함께 답변합니다.",
};

export async function* previewStream(message: string): AsyncGenerator<StreamEvent> {
  yield { type: "status", phase: "searching" };
  yield { type: "exploration", step: "frontend/src/app/analyze/page.tsx 확인" };
  await new Promise((resolve) => setTimeout(resolve, 220));
  yield { type: "status", phase: "building_context" };
  const answer = /구조|architecture|아키텍처/i.test(message)
    ? PREVIEW_ANSWERS.architecture
    : PREVIEW_ANSWERS.default;
  yield { type: "status", phase: "generating" };
  for (let index = 0; index < answer.length; index += 18) {
    yield { type: "content", content: answer.slice(index, index + 18) };
    await new Promise((resolve) => setTimeout(resolve, 18));
  }
  yield {
    type: "references",
    references: [{
      file: "frontend/src/app/analyze/page.tsx",
      line: 1,
      language: "TypeScript",
      snippet: "export default function AnalyzePage()",
    }],
  };
  yield { type: "done" };
}
