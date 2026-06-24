# CodeMap AI 멀티에이전트 아키텍처 도입 및 병렬 처리 최적화 제안서

> [!NOTE]
> 최종 합의안 기준 문서입니다. 백엔드 agent 구현, LangGraph State 설계, API 명세 수정 시 본 문서를 기준으로 삼습니다.
>
> 관련 시각 자료:
>
> - [로직/흐름 다이어그램](../02_Architecture/MULTIAGENT_LOGIC_DIAGRAM.html)
> - [발표용 시각화 자료](../02_Architecture/MULTIAGENT_VISUAL_OVERVIEW.html)

본 문서는 CodeMap AI의 백엔드 시스템에서 발생할 수 있는 보안/오작동 문제를 해결하기 위한 **멀티에이전트 분리 아키텍처**, 대규모 분석 시 우려되는 지연 시간(Latency)을 해결하기 위한 **비동기 병렬 처리**, 그리고 LLM 릴레이 대화 시 발생하는 정보 유실을 막기 위한 **LangGraph State 공유 및 Decoupled 패턴**을 통합한 최종 합의안 명세서입니다.

---

## 1. 기존 아키텍처의 한계 및 제안 배경

기존 단일 만능 에이전트(Single God Agent)에 모든 도구를 쥐어주거나, 에이전트들이 서로 릴레이 방식으로 대화하는 구조는 다음과 같은 한계를 가집니다.

1. **보안 취약성 (Access Control Breach)**
   악의적인 프롬프트 인젝션으로 전역 경로 조회를 지시할 때, 도구를 가진 LLM 스스로가 이를 방어하기 어렵습니다. 보안 통제는 예측 불가능한 LLM이 아닌 결정론적(Deterministic) 코드가 맡아야 합니다.
2. **도구 오선택 (Tool Hallucination)**
   단일 LLM에 너무 많은 도구 스키마(Tool Schema)를 제공하면 매개변수 매핑 오류나 엉뚱한 도구를 호출하는 오작동률이 증가합니다.
3. **정보 유실 (Whisper Down the Lane)**
   앞선 에이전트의 결과를 뒤의 에이전트가 요약해서 넘겨주는 직렬 구조는, 응답 속도를 저하시킬 뿐만 아니라 개발자에게 가장 중요한 **날 것의 소스 코드 원본(Raw Data)** 을 중간에 손실시킬 수 있습니다.
4. **스트리밍(SSE) 구현의 복잡성**
   깊은 멀티에이전트 워크플로우 내부에서 최종 답변 스트리밍까지 처리하면 아키텍처가 불필요하게 복잡해질 수 있습니다.

---

## 2. 핵심 아키텍처: State 공유 및 역할 분리

본 제안서의 핵심은 **LangGraph를 통한 물리적/논리적 도구 격리**, **State(공유 메모리)를 활용한 원본 데이터 보존**, 그리고 **Application Layer로의 프레젠테이션(Final Answer) 로직 분리**입니다.

### 역할 및 책임(R&R) 상세 정의

#### Application Layer (프레젠테이션 계층)

이 계층은 사용자와 직접 소통하며 답변을 스트리밍하는 데 집중합니다.

**1. `app/chat/service` (API 라우터 및 스트리밍 관리자)**

- 역할: 애플리케이션의 진입점입니다.
- LangGraph 엔진을 호출하여 검색을 지시합니다.
- LangGraph 실행 결과를 받아 SSE 스트리밍을 제어합니다.
- LLM agent가 아닌 일반 코드 계층입니다.

**2. `Final Answer Agent` (요약 및 생성 전담 LLM)**

- 역할: LangGraph 워크플로우 밖, 즉 Application Layer에 위치합니다.
- LangGraph가 반환한 State의 훼손되지 않은 원본 코드들을 직접 읽습니다.
- 사용자에게 제공할 최종 답변을 작성하고 스트리밍합니다.

#### LangGraph Execution Engine (데이터 수집 계층)

이 계층은 빠르고 정확하게 소스코드를 탐색하여 원본 데이터를 수집하는 데 집중합니다.

**3. `Supervisor Agent` (계획 수립 LLM)**

- 오타를 교정하고(Query Rewrite) 사용자의 의도를 분석합니다.
- 어떤 도구로 어느 경로를 탐색할지 상위 계획(`access_plan`)을 세웁니다.
- 계획 결과를 State에 저장합니다.
- 로컬 I/O 도구는 갖지 않습니다.

**4. `Route Node` (보안 통제 및 라우팅)**

- LLM이 아닌 100% 일반 코드입니다.
- Supervisor의 계획을 읽어 Allowlist(허용 경로)를 검증합니다.
- Path Traversal 공격을 차단합니다.
- 권한이 확인된 Worker들을 비동기 병렬(Parallel)로 라우팅합니다.
- Worker 결과를 자연어로 요약하지 않습니다.

**5. `Tool Workers` (단일 목적 실행기)**

- `Search Worker`(LLM), `Dir Worker`(코드 래퍼), `Grep Worker`(코드 래퍼), `Read Worker`(코드 래퍼), 선택형 `Code Reasoning Worker`(LLM)로 나눕니다.
- 각 Worker는 하나의 도구 또는 하나의 책임만 전담합니다.
- 실행 결과를 상위 제어 노드에 요약해서 돌려주지 않습니다.
- 실행 결과를 날 것 그대로(Raw Data) State 공유 메모리에 직접 병합(Append)합니다.

---

## 3. 병렬 처리 및 State 공유 구조

### 3-1. 비동기 병렬 처리 (Latency 극복)

Supervisor가 "특정 폴더 구조를 탐색(`dir`)하고, 동시에 키워드를 검색(`grep`)하라"고 계획을 내렸을 때, `Route Node` 코드는 두 Worker를 직렬로 기다리지 않습니다.

파이썬의 `asyncio.gather` 또는 LangGraph의 parallel branch를 이용해 여러 Worker를 동시에 비동기로 실행함으로써, 다수의 도구를 사용하더라도 응답 지연을 방어하고 퍼포먼스를 높입니다.

### 3-2. `CodeMapState` 공유 메모리 (정보 유실 방어)

에이전트들이 서로의 결과를 요약해서 텍스트로 전달하지 않고, 아래와 같은 중앙 State 객체에 데이터를 기록하고 읽습니다.

```python
from typing import TypedDict


class CodeMapState(TypedDict):
    user_query: str           # 사용자의 원본 질문
    rewritten_query: str      # Supervisor가 교정한 검색용 질의
    access_plan: list         # Supervisor가 수립한 허용 도구 및 경로 목록
    security_result: dict     # Route Node의 allowlist/path traversal 검증 결과
    worker_results: list      # Worker들이 수집한 요약되지 않은 원본 소스코드
    compact_context: dict     # Evidence Aggregator가 정리한 근거 묶음
    final_answer: str | None  # Final Answer Agent가 생성한 최종 응답
```

이 구조 덕분에 Application Layer의 `Final Answer Agent`는 누군가에 의해 축약되지 않은 코드 스니펫(`worker_results`)과 Evidence Aggregator가 정리한 `compact_context`를 직접 열람하고 근거 기반 답변을 작성할 수 있습니다.

---

## 4. 백엔드 디렉토리 구조 수정 제안 (`backend/app/`)

위의 최종 합의된 아키텍처 결정을 반영하여, 계층(Layer)을 명확히 격리하는 디렉토리 구조를 제안합니다.

> [!NOTE]
> 아래 구조는 현재 코드에 이미 모두 존재한다는 의미가 아니라, agent 기능 구현 시 맞춰갈 **목표 디렉토리 구조**입니다.
> `Final Answer Agent`는 LangGraph 데이터 수집 계층 밖의 `chat/` Application Layer에 위치합니다.

```text
CodeMap/backend/app/
├── core/
│
├── chat/                       # 1. Application Layer: 프레젠테이션 및 스트리밍 응답
│   ├── __init__.py
│   ├── router.py               # 대화 API 및 SSE 엔드포인트
│   ├── service.py              # LangGraph 엔진 비동기 호출 및 SSE 이벤트 제어 로직
│   └── final_answer_agent.py   # Final Answer Agent: State 원본 기반 최종 응답 생성
│
├── agent_graph/                # 2. LangGraph Layer: State, Nodes, Agents, Workers
│   ├── __init__.py
│   ├── state.py                # CodeMapState 공유 상태 정의
│   ├── graph.py                # LangGraph Workflow 정의부 (Node, Edge, StateGraph)
│   ├── agents/                 # LLM agent 객체 정의
│   │   └── supervisor_agent.py # Supervisor Agent: 계획 수립 및 쿼리 재작성
│   ├── nodes/                  # 일반 코드 node 정의
│   │   ├── route_node.py       # Deterministic Router: 경로 보안 검증 및 Worker 병렬 라우팅
│   │   └── evidence_node.py    # Evidence Aggregator: 중복 제거 및 token budget 압축
│   ├── tools/                  # 개별 도구 물리 명세
│   │   ├── dir.py
│   │   ├── grep.py
│   │   ├── read.py
│   │   └── search.py
│   └── workers/                # 도구 전담 단일 목적 에이전트/래퍼 선언부
│       ├── search_worker.py
│       ├── dir_worker.py
│       ├── grep_worker.py
│       ├── read_worker.py
│       └── reasoning_worker.py # 선택형 Code Reasoning Worker
```

---

## 5. 최종 기대 효과 및 장점 요약

1. **스트리밍(SSE) 최적화와 결합도 최소화**

   무거운 데이터 수집 그래프 엔진(LangGraph)과 화면에 텍스트를 제공하는 요약 에이전트(Final Answer)를 분리하여 시스템의 유지보수성과 재사용성을 높입니다.
2. **보안 및 신뢰성 강화**

   실행 통제자(Route Node)에서 LLM을 배제하고 순수 코드로 제어함으로써, 시스템 경로 우회(Path Traversal) 공격 등 보안 위협을 차단합니다.
3. **응답 지연(Latency) 방어 및 도구 오작동 감소**

   Worker 비동기 병렬 실행으로 체감 대기 시간을 줄이고, 도구를 하나씩만 쥐여주어 도구 오작동(Hallucination) 확률을 낮춥니다.
4. **원본 데이터 보존 (No Information Loss)**

   중간 요약 과정 없이 Raw Data를 State 메모리에 직접 기록하는 구조를 채택하여, 코딩 어시스턴트에서 중요한 실제 코드 스니펫 원형이 답변 생성 과정에서 손실되는 문제를 방지합니다.

> [!IMPORTANT]
> 본 아키텍처 제안이 최종 확정됨에 따라, 백엔드 개발 시 본 문서의 **디렉토리 구조**와 **CodeMapState 스키마**를 표준 기준으로 삼아 구현을 진행합니다.
