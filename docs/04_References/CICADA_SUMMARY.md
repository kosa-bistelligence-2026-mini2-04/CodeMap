# wende/cicada 요약 및 분석

**wende/cicada**는 AI 코딩 어시스턴트에게 추상 구문 트리(AST) 기반의 구조적 코드 인텔리전스를 제공하도록 설계된 **MCP (Model Context Protocol) 서버** 도구입니다. 기존의 텍스트 검색(grep)을 넘어 AI가 코드베이스를 더 효율적으로 탐색하고 구조를 깊이 이해할 수 있도록 돕습니다.

## 📌 핵심 요약 (Core Highlights)

- **AST 기반 코드 인텔리전스 (AST-Powered Intelligence)**: 코드를 단순 텍스트 파일로 취급하는 대신 Tree-sitter를 활용해 AST로 파싱합니다. 이를 통해 심볼, 함수 시그니처, 타입 사양 및 문서를 정확한 위치 정보와 함께 추출합니다.
- **토큰 효율성 향상 (Context Compaction)**: 대용량 파일을 AI의 컨텍스트 윈도우에 통째로 넣는 대신, 요약이나 함수 시그니처, 호출 위치(Call sites) 등 구조적으로 연관된 컨텍스트만 선별하여 제공하므로 토큰 사용량을 대폭 줄이고 에이전트의 추론 속도를 높입니다.
- **다국어 지원**: Elixir, Python, TypeScript, JavaScript, Rust, Go 등 17개 이상의 프로그래밍 언어를 지원하여 언어에 구애받지 않는 분석 환경을 제공합니다.
- **Git 및 PR 연동 (PR Attribution)**: Git 히스토리와 연동하여 특정 코드 라인을 Pull Request, 코드 리뷰 및 설계 결정 사항과 연결하는 역사적 맥락(Historical context)을 제공합니다.

## ⚙️ 기술 스택
- **코드 파서**: Tree-sitter (AST 구문 분석)
- **통신 프로토콜**: MCP (Model Context Protocol)
- **기반 언어/환경**: Python 기반 도구 (패키지 관리/의존성: `uv`, 테스트: `pytest`, 포맷터/린터: `black`, `ruff`)

## 🏗️ 주요 아키텍처 및 파이프라인 흐름

### 1. 지식 그래프 구축 (Knowledge Graph Construction)
- Tree-sitter로 구문을 분석하여 호출 그래프(Call graphs), 종속성 추적(Imports/Aliases), 파일 간의 관계 등 구조적 맵을 생성하고, 코드베이스의 영구 인덱스(주로 `~/.cicada`에 저장)를 구축합니다.
- 파일이 변경될 때마다 백그라운드에서 인덱스를 점진적(Incremental)으로 업데이트하여 현재 코드베이스 상태와 지식 그래프를 동기화합니다.

### 2. 의미론적 검색 (Semantic Search)
- 구조적 맵을 유지하기 때문에 단순한 텍스트 기반 검색을 넘어섭니다. 예를 들어 "인증(authentication)"과 같은 개념적인 쿼리에도, 코드 문서에 해당 단어가 명시되지 않은 관련 함수와 모듈을 효과적으로 표출합니다.
- AI 에이전트는 코드 리팩토링이나 기능 구현 시 이 구조를 참조하여, 변경 사항이 미칠 영향을 미리 파악할 수 있습니다.

### 3. MCP 통합 (MCP Integration)
- 표준화된 클라이언트-서버 아키텍처를 따릅니다. 호스트(Claude Desktop이나 IDE 내 AI 에이전트)가 Cicada MCP 서버에 특정 컨텍스트(함수 정의, 모듈 검색 등)를 요청하면, 서버가 구조화된 응답을 반환하여 표준화된 방식으로 프로젝트 코드베이스와 상호작용합니다.
