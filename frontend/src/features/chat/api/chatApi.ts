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

/**
 * Run stream SSE 이벤트 타입.
 * 백엔드 Run stream의 원본 이벤트를 직접 수신합니다.
 */
export interface StreamEvent {
  type:
    | "graph_started"
    | "planner_plan"
    | "route_validated"
    | "worker_started"
    | "worker_result"
    | "evidence_compacted"
    | "answer_delta"
    | "references"
    | "completed"
    | "cancelled"
    | "failed"
    | "error";
  // graph_started
  runId?: string;
  stateKeys?: string[];
  // planner_plan
  rewrittenQuery?: string;
  selectedWorkers?: string[];
  allowedPaths?: string[];
  // route_validated
  parallelGroups?: Array<{ worker: string; path: string }>;
  // worker_result
  worker?: string;
  target?: string | null;
  resultCount?: number;
  evidenceIds?: string[];
  // evidence_compacted
  evidenceCount?: number;
  compactContextReady?: boolean;
  // answer_delta
  content?: string;
  // references
  references?: CodeReference[];
  // failed / error
  error?: string;
  status?: string;
  cancelledAt?: string | number;
  // sessionId (from create_chat_run response)
  sessionId?: string;
}

export function describeStreamTimelineStep(event: StreamEvent): string | null {
  switch (event.type) {
    case "graph_started":
      return event.runId ? `Run ${event.runId} 실행을 시작했습니다.` : "Run 실행을 시작했습니다.";
    case "planner_plan": {
      const workers = event.selectedWorkers?.length ? event.selectedWorkers.join(", ") : "전체 스캔";
      const query = event.rewrittenQuery ? ` — ${event.rewrittenQuery}` : "";
      return `계획 수립: [${workers}]${query}`;
    }
    case "route_validated": {
      const count = event.parallelGroups?.length || 0;
      return `에이전트 작업 ${count}개를 검증했습니다.`;
    }
    case "worker_started": {
      const target = event.target ? ` (${event.target})` : "";
      return `${event.worker || "worker"} worker가 실행을 시작했습니다${target}.`;
    }
    case "worker_result": {
      const evidenceText = event.evidenceIds?.length ? ` — ${event.evidenceIds.length}개 ID 확인` : "";
      return `${event.worker || "worker"} worker가 근거 ${event.resultCount || 0}개를 수집했습니다${evidenceText}.`;
    }
    case "evidence_compacted": {
      const count = typeof event.evidenceCount === "number" ? event.evidenceCount : event.resultCount;
      const countText = typeof count === "number" ? ` ${count}개` : "";
      return `수집 근거${countText}를 답변 컨텍스트로 압축했습니다.`;
    }
    case "references": {
      const count = event.references?.length || 0;
      return `참조 파일 ${count}개를 답변에 연결했습니다.`;
    }
    case "completed":
      return "Run이 정상 완료되었습니다.";
    case "cancelled":
      return "Run이 취소되었습니다.";
    case "failed":
    case "error":
      return `Run 처리 중 오류가 발생했습니다: ${event.error || "원인 미상"}`;
    default:
      return null;
  }
}

interface StreamChatOptions {
  threadId?: string | null;
  contextFile?: string | null;
}

const MODE_MAP: Record<ChatMode, string> = {
  quick: "lite",
  deep: "deep",
};

/**
 * 2단계 Run API를 사용하여 채팅을 스트리밍합니다.
 *
 * 1) POST /api/chat/{repoId}/runs → run 생성, streamUrl 반환
 * 2) GET  streamUrl → SSE 스트리밍
 */
export async function* streamChat(
  repoId: string,
  message: string,
  mode: ChatMode,
  options: StreamChatOptions = {},
): AsyncGenerator<StreamEvent> {
  // Step 1: Run 생성
  let runData: { runId: string; sessionId: string; streamUrl: string };
  try {
    const response = await fetch(apiPath(`/chat/${repoId}/runs`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: message,
        mode: MODE_MAP[mode] || "lite",
        sessionId: options.threadId || undefined,
      }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      yield {
        type: "error",
        error: payload?.detail || `채팅 요청에 실패했습니다. (${response.status})`,
      };
      return;
    }
    const json = await response.json();
    runData = json.data;
  } catch {
    yield { type: "error", error: "채팅 서버에 연결할 수 없습니다. 백엔드 상태를 확인해주세요." };
    return;
  }

  // sessionId를 graph_started 이벤트에 포함하여 전달
  yield { type: "graph_started", runId: runData.runId, sessionId: runData.sessionId };

  // Step 2: SSE 스트리밍
  let streamResponse: Response;
  try {
    streamResponse = await fetch(apiPath(runData.streamUrl.replace("/api", "")));
  } catch {
    yield { type: "error", error: "스트리밍 연결에 실패했습니다." };
    return;
  }

  if (!streamResponse.ok || !streamResponse.body) {
    yield { type: "error", error: `스트리밍 연결 실패 (${streamResponse.status})` };
    return;
  }

  const reader = streamResponse.body.getReader();
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
  yield { type: "graph_started", runId: "preview" };
  yield { type: "route_validated", parallelGroups: [{ worker: "search_worker", path: "frontend/src/app/analyze/page.tsx" }] };
  yield { type: "worker_started", worker: "search", target: "frontend/src/app/analyze/page.tsx" };
  await new Promise((resolve) => setTimeout(resolve, 220));
  yield { type: "worker_result", worker: "search", resultCount: 1 };
  yield { type: "evidence_compacted" };
  const answer = /구조|architecture|아키텍처/i.test(message)
    ? PREVIEW_ANSWERS.architecture
    : PREVIEW_ANSWERS.default;
  for (let index = 0; index < answer.length; index += 18) {
    yield { type: "answer_delta", content: answer.slice(index, index + 18) };
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
  yield { type: "completed", runId: "preview", status: "completed" };
}
