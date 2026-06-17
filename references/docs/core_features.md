# CodeMap AI 프로젝트 핵심 기능 명세서 (v4)

MVP(최소 기능 제품) 구현을 위한 **Phase 1(핵심 기능)**과 이후 점진적으로 도입할 **Phase 2(고도화 추가 기능)**으로 분할하여 관리합니다. 기존에 정의된 모든 세부 기능들을 하나도 누락 없이 유지하면서, 작업 할당과 역할 분담의 명확성을 위해 철저한 **도메인 주도 설계(DDD) 기반의 새로운 기능 ID 규칙**을 전면 적용했습니다.

> [!NOTE]
> 🏗️ **기능 ID 명명 규칙 (Domain-Driven Naming Convention)**
> 
> 모든 기능의 최종 코드는 `{대분류ID}-{모듈명}-{F/B}-{3자리_번호}` 형식을 따릅니다.
> 
> - **대분류 ID**: `PROJECT`, `RAG`, `AGENT`, `DOCS`, `COMMON`
> - **모듈명**: 도메인 내 세부 서브모듈 (예: `REPO`, `PARSE`, `EMBED`, `WS` 등)
> - **F/B**: 개발 계층 (F: Frontend, B: Backend)
> - **3자리 번호**: 아키텍처 폴더/계층 매핑
>   - **프론트엔드 (F)**: `1xx` (Pages), `2xx` (UI Components), `3xx` (API Hooks), `4xx` (Store/Context), `5xx` (Types/Utils)
>   - **백엔드 (B)**: `1xx` (Router), `2xx` (Service), `3xx` (Repository), `4xx` (Schemas), `5xx` (Models)

---

## 1️⃣ Phase 1: 프로젝트 등록 (Git 클론 및 지능형 필터링)

| ID | 대분류 | 모듈 | 기능명 | 대상 파일 | 상세 설명 | 완료 기준 | 담당자 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PROJECT-REPO-F-101** | PROJECT | REPO | 저장소 연동 진입 페이지 | `app/page.tsx` | 저장소를 입력받기 위한 랜딩 페이지 메인 View 렌더링 | 페이지 정상 렌더링 및 입력 폼 컴포넌트 마운트 시 | |
| **PROJECT-REPO-F-201** | PROJECT | REPO | GitHub URL 입력 UI | `components/RepoInput.tsx` | 사용자가 GitHub 저장소 URL을 입력할 수 있는 입력 폼 제공 및 검증 | URL 유효성 검증 통과 및 분석 API 호출 버튼 활성화 시 | |
| **PROJECT-LIST-F-201** | PROJECT | LIST | 분석 이력 목록 화면 | `components/HistoryList.tsx` | 이미 분석한 레포 목록과 각 분석 상태(완료/진행/실패) 조회 화면 | DB 캐싱 데이터가 리스트 형태로 정상 렌더링 될 시 | |
| **PROJECT-REPO-B-101** | PROJECT | REPO | 프로젝트 등록 API | `api/routes.py` | `POST /api/analysis` 요청을 받아 분석 파이프라인 초기화 (Router) | Job ID 반환 및 HTTP 200/202 응답 성공 시 | |
| **PROJECT-LIST-B-101** | PROJECT | LIST | 레포 목록 조회 API | `api/routes.py` | `GET /api/analysis` 전체 분석 이력 목록 반환 (Router) | 기존에 분석된 프로젝트 이력 배열이 JSON으로 반환될 시 | |
| **PROJECT-REPO-B-201** | PROJECT | REPO | Git 저장소 URL 검증 | `services/repo_cloner.py` | GitHub URL 형식 유효성 검사 및 로컬 경로 예외 처리 (Service) | 유효하지 않은 URL 입력 시 적절한 에러 로그 반환 시 | |
| **PROJECT-REPO-B-202** | PROJECT | REPO | 레포 크기/파일 수 사전 검증 | `services/repo_cloner.py` | clone 전 파일 수·용량이 제한 초과 여부 확인 및 초과 시 안내 (Service) | 제한 초과 저장소 감지 시 다운로드 중단 및 예외 처리 시 | |
| **PROJECT-REPO-B-203** | PROJECT | REPO | Git Clone 및 파일 필터링 | `services/repo_cloner.py` | 임시 디렉토리 복제 후 `node_modules`, `build`, 바이너리 파일 자동 제외 (Service) | 불필요 파일 스킵 로그 확인 및 타겟 파일만 복제 성공 시 | |
| **PROJECT-REPO-B-204** | PROJECT | REPO | Clone Timeout 예외 처리 | `services/repo_cloner.py` | timeout seconds 설정, 에러 캡처, 실패 시 cleanup (Service) | 타임아웃 발생 시 임시 폴더 삭제 및 프로세스 종료 시 | |
| **PROJECT-REPO-B-301** | PROJECT | REPO | 프로젝트 메타데이터 저장 | `services/analysis_store.py`| repo_name, owner, branch, clone_path를 DB/메모리에 저장 (Repository) | 상태 업데이트 요청 시 정상적으로 스토리지 값이 변경될 시 | |

---

## 2️⃣ Phase 1: 코드 맥락 및 관계망 이해 (RAG 및 코드 임베딩)

| ID | 대분류 | 모듈 | 기능명 | 대상 파일 | 상세 설명 | 완료 기준 | 담당자 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RAG-VIEW-F-201** | RAG | VIEW | 구조 분석 결과 표시 UI | `components/ReportViewer.tsx`| 파일 트리, 기술 스택, 진입점 탐지 결과를 화면에 시각적으로 표시 | 파싱된 배열 데이터가 구조화된 UI 탭에 정상 렌더링 될 시 | |
| **RAG-CHART-F-201**| RAG | CHART | 파일 리스크 히트맵 시각화 | `components/HeatmapChart.tsx`| 분석 데이터를 기반으로 위험도 분포 트리맵 시각화 UI 컴포넌트 | 위험도 점수에 따라 적색~녹색으로 차트가 그려질 시 | |
| **RAG-API-B-101** | RAG | API | 분석 결과 조회 API | `api/routes.py` | `GET /api/analysis/{repo_id}` 분석된 RAG 결과 데이터 반환 (Router) | 요청된 Repo ID에 맞는 메타데이터 및 분석 결과 반환 시 | |
| **RAG-PARSE-B-201**| RAG | PARSE | 디렉토리 구조 분석 | `agents/code_mapper.py` | 프로젝트 폴더 트리 구조 및 물리적 아키텍처 맵 생성 (Service) | 전체 폴더 트리가 계층형 JSON(또는 Text)으로 파싱될 시 | |
| **RAG-PARSE-B-202**| RAG | PARSE | 파일 간 import 관계 분석 | `agents/code_mapper.py` | 파일 모듈 간 의존 파일 목록 추출 및 유기적 관계망 지도 구축 (Service) | 순환 참조를 배제한 Import 흐름 트리가 정상 추출될 시 | |
| **RAG-PARSE-B-203**| RAG | PARSE | 핵심 파일 탐색 (Entry Point) | `agents/code_mapper.py` | `main.py`, `App.tsx` 등 진입점(Entry point) 자동 탐색 (Service) | 프로젝트 구동의 진입점이 되는 핵심 파일 경로가 반환될 시 | |
| **RAG-CONF-B-201** | RAG | CONF | 설정 파일 및 README 분석 | `agents/doc_generator.py` | `package.json`, `README.md` 등을 기반으로 목적 및 핵심 기능 추출 (Service) | 프로젝트의 주요 목적과 사용 라이브러리가 식별될 시 | |
| **RAG-CONF-B-202** | RAG | CONF | 기술 스택 및 실행 방법 추론 | `agents/doc_generator.py` | 프레임워크·런타임 자동 탐지 및 install/run 커맨드 자동 생성 (Service) | 실행에 필요한 쉘(Shell) 명령어 스니펫이 정상 생성될 시 | |
| **RAG-AST-B-201** | RAG | AST | AST 기반 코드 청킹 | `agents/code_mapper.py` | 함수/클래스 단위 코드 분리 및 임베딩을 위한 청킹(Chunking) (Service) | 대용량 파일이 논리적인 함수 단위 배열로 쪼개질 시 | |
| **RAG-EMBED-B-201**| RAG | EMBED | 임베딩 벡터 생성 | `services/analysis_store.py`| 파싱된 데이터(코드 및 문서)를 OpenAI 임베딩 후 벡터화 (Service) | 1536차원(또는 지정된 차원)의 Float 배열이 정상 생성될 시 | |
| **RAG-DB-B-301** | RAG | DB | pgvector 기반 DB 저장 | `services/analysis_store.py`| 생성된 임베딩 및 메타데이터를 pgvector 등 벡터 DB에 적재 (Repository) | DB Insert 후 Vector Search 쿼리가 정상 작동할 시 | |

---

## 3️⃣ Phase 1: 자율 탐색형 AI 코드 분석 (Agentic Search)

| ID | 대분류 | 모듈 | 기능명 | 대상 파일 | 상세 설명 | 완료 기준 | 담당자 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AGENT-WS-F-201** | AGENT | WS | 실시간 진행 패널 (출처 포함)| `components/ProgressPanel.tsx`| 실시간 진행률 표시, 로그 출력 시 참조한 소스코드 파일명/줄번호 제공 | 소켓 로그 메시지와 퍼센티지 바(Bar)가 동기화되어 채워질 시 | |
| **AGENT-TIME-F-201**| AGENT | TIME | 에이전트 소요 시간 시각화 | `components/AgentDurationsPanel.tsx`| 각 AI 에이전트 소요 통계(ms)를 시각화하여 파이프라인 병목 확인 | 각 에이전트별 처리 시간 막대 차트가 정상 렌더링될 시 | |
| **AGENT-WS-F-301** | AGENT | WS | WebSocket 커스텀 훅 | `hooks/useWebSocket.ts` | 클라이언트 소켓 연결, 재연결, 상태 관리를 담당하는 API Hook | 소켓 끊김 시 자동 재연결(Reconnection) 로직이 작동할 시 | |
| **AGENT-WS-B-101** | AGENT | WS | 진행 상황 스트리밍 버스 | `api/progress_bus.py` | 에이전트의 상태/로그를 모아 WebSocket 채널로 브로드캐스트 (Router) | 서버 측에서 클라이언트로 Event 메세지가 정상 Push될 시 | |
| **AGENT-ORCH-B-201**| AGENT | ORCH | 다중 에이전트 오케스트레이터 | `orchestrator/planner.py` | 하위 에이전트들의 실행 순서(DAG) 수립 및 비동기 병렬 실행 제어 (Service) | 의존성 위배 없이 다중 에이전트 Task가 병렬 완수될 시 | |
| **AGENT-JUDGE-B-201**| AGENT | JUDGE | 자가 교정 및 충돌 조율 | `agents/onboarding_guide.py`| 탐색 실패 시 다른 경로 탐색(Self-Correction), LLM Judge로 의견 충돌 조율 | 실패 시 3~5회 이내 재탐색 시도 후 조율 결과가 반환될 시 | |

---

## 4️⃣ Phase 1: 계층형 프로젝트 가이드북 자동 생성 (Map-Reduce 문서화)

| ID | 대분류 | 모듈 | 기능명 | 대상 파일 | 상세 설명 | 완료 기준 | 담당자 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DOCS-VIEW-F-101** | DOCS | VIEW | 분석 메인 페이지 조립 | `app/analyze/page.tsx` | Dashboard View 진입점, 진행 패널 및 리포트 뷰어 통합 조립 (Page) | 하위 컴포넌트들이 의도된 레이아웃(Grid/Flex)으로 배치될 시 | |
| **DOCS-VIEW-F-201** | DOCS | VIEW | 마스터 리포트 뷰어 | `components/ReportViewer.tsx`| JSON/Markdown 데이터를 받아 요약, 취약점 등 탭 형태로 분리 렌더링 | XSS 이슈 없이 최종 가이드북 마크다운이 HTML로 파싱될 시 | |
| **DOCS-VIEW-F-501** | DOCS | VIEW | HTML XSS 살균 유틸리티 | `lib/sanitize.ts` | DOMPurify 등을 활용해 마크다운 렌더링 시 발생할 수 있는 보안 취약점 방어 | 악의적인 `<script>` 태그 주입 시 안전하게 필터링될 시 | |
| **DOCS-GEN-B-201** | DOCS | GEN | 계층형 Bottom-up 요약 로직 | `agents/onboarding_guide.py`| 파일 요약 → 폴더 요약 → 마스터 요약 순서로 상향식 문서화 수행 (Service) | Tree-based RAG 로직으로 프로젝트 전체 마스터 요약 생성 시 | |

---

## 5️⃣ COMMON (공통 레이아웃 및 글로벌 상태)

| ID | 대분류 | 모듈 | 기능명 | 대상 파일 | 상세 설명 | 완료 기준 | 담당자 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **COMMON-CTX-F-401**| COMMON| CTX | 다국어 및 테마 상태 관리 | `contexts/AppContext.tsx` | i18n(한국어/영어) 및 Light/Dark 테마 상태를 관리하는 전역 Store | 토글 버튼 클릭 시 로컬 스토리지 값 및 앱 전체 테마 변경 시 | |
| **COMMON-TYPE-F-501**| COMMON| TYPE | 클라이언트 DTO 타입 정의 | `types/contracts.ts` | 백엔드 API 명세와 일치하는 프론트엔드 Typescript 인터페이스 | 백엔드 통신 시 TS 컴파일 에러가 발생하지 않을 시 | |
| **COMMON-TYPE-B-401**| COMMON| TYPE | Pydantic Request/Response | `models/schemas.py` | API 데이터 유효성 검사 및 응답 직렬화를 위한 스키마 (Schemas) | 잘못된 payload 전송 시 422 Validation Error가 반환될 시 | |

---

## 🥈 Phase 2: 고도화 추가 기능 (MVP 이후 확장)

| ID | 대분류 | 모듈 | 기능명 | 상세 설명 | 도입 예상 시점 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **EXT-NOTI-B-101** | EXT | NOTI | Slack / Discord 알림 | 분석이 완료되면 팀 메신저 채널로 핵심 요약 리포트 푸시 전송 | Phase 1 완료 직후 |
| **EXT-CHAT-F-201** | EXT | CHAT | 자연어 질문 해석(Q&A) | 문맥을 파악해 의도에 맞는 소스코드를 정확히 찾아주는 대화형 챗봇 패널 | Phase 2 핵심 기능 |
| **EXT-DOWN-F-201** | EXT | DOWN | 리포트 PDF/MD 다운로드 | 완성된 가이드북을 깔끔한 디자인의 PDF 및 Markdown 포맷으로 추출 | Phase 2 초기 |
