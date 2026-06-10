# Codebase Onboarding Reference Comparison

이 문서는 CodeCompass 팀 프로젝트에서 참고할 20개 레퍼런스의 특징을 프론트엔드, 백엔드/RAG, 운영 구조 관점으로 비교한 자료입니다.

## 전체 비교표

| 레퍼런스 폴더 | 원본 GitHub | 프론트 참고도 | 백엔드/RAG 참고도 | 눈여겨볼 특징 |
| --- | --- | --- | --- | --- |
| `projects/403errors__repomind` | https://github.com/403errors/repomind | 매우 높음 | 매우 높음 | 가장 제품형에 가까움. 랜딩, repo search, chat, file preview, architecture map, security scan, streaming progress 참고 |
| `projects/CraftFossLabs__chatrepos.ai` | https://github.com/CraftFossLabs/chatrepos.ai | 높음 | 중 | ChatGPT형 대화 UI, Next.js, shadcn, Zustand, Mermaid 사용. 간결한 repo analyzer UX 참고 |
| `projects/chroma-core__github-sync-demo` | https://github.com/chroma-core/github-sync-demo | 높음 | 높음 | Next.js + Chroma + AI SDK. GitHub repo sync, ChromaDB 연동, chat UX 참고 |
| `projects/MatheusAFD__repo-lens` | https://github.com/MatheusAFD/repo-lens | 높음 | 중상 | 모노레포, Turbo, Playwright e2e, packages/ui, NestJS API. 제품 운영 구조 참고 |
| `projects/CronusL-1141__repo-insight` | https://github.com/CronusL-1141/repo-insight | 중상 | 매우 높음 | 4-agent 병렬 분석, WebSocket progress, SQLite history, ECharts heatmap, guardrail, timeout fallback |
| `projects/HarishChandran3304__TTG` | https://github.com/HarishChandran3304/TTG | 매우 높음 | 중상 | 우리 아이디어와 가장 유사. FastAPI + React/Vite + Gemini, GitHub URL 기반 repo chat |
| `projects/Manas2412__CodeBase-Q-A-with-RAG` | https://github.com/Manas2412/CodeBase-Q-A-with-RAG | 중 | 매우 높음 | clone -> tree-sitter AST chunking -> Voyage embedding -> pgvector -> HyDE -> rerank -> Ollama SSE streaming |
| `projects/Neverdecel__CodeRAG` | https://github.com/Neverdecel/CodeRAG | 낮음~중 | 매우 높음 | 코드베이스 RAG 라이브러리 구조. chunking, retrieval, sqlite store, vector index, CLI/API/Streamlit surface 분리 |
| `projects/amrgaberM__CodeBase-Intelligence` | https://github.com/amrgaberM/CodeBase-Intelligence | 중 | 매우 높음 | AST parser, dependency graph, BM25 + vector hybrid retrieval, reranker, query expander, evaluator |
| `projects/wende__cicada` | https://github.com/wende/cicada | 낮음 | 매우 높음 | AST-level indexing, call-site tracking, semantic search, PR attribution, 17+ 언어 지원 |
| `projects/jurasofish__mcpunk` | https://github.com/jurasofish/mcpunk | 낮음 | 높음 | embedding 없이 logical chunk + search tool로 코드베이스를 탐색하는 방식 |
| `projects/kvnpetit__structured-repo-context-mcp` | https://github.com/kvnpetit/structured-repo-context-mcp | 낮음 | 높음 | MCP 서버, tree-sitter, LanceDB, Ollama embedding, CLI/server/tool 분리 |
| `projects/probelabs__docs-mcp` | https://github.com/probelabs/docs-mcp | 낮음 | 중상 | Git repo/docs를 MCP 검색 서버로 만드는 구조. tar.gz 다운로드, dynamic config, auto update 참고 |
| `projects/Thibault-Knobloch__codebase-intelligence` | https://github.com/Thibault-Knobloch/codebase-intelligence | 낮음 | 중상 | CLI 중심 codebase indexing/querying. fetch/refinement/vector_db/agent 구조가 단순해 MVP 참고용 |
| `projects/mehmoodosman__codebase-rag` | https://github.com/mehmoodosman/codebase-rag | 중 | 중 | Streamlit + Pinecone + HuggingFace embedding + Groq. 최소 RAG 데모 구조 참고 |
| `projects/danielefavi__ai-codebase-assistant` | https://github.com/danielefavi/ai-codebase-assistant | 낮음~중 | 중 | LangChain + Chroma + Ollama 기반 codebase assistant. local LLM/RAG 구조 참고 |
| `projects/aniketkarne__AI-Powered-Github-Repo-Analyzer` | https://github.com/aniketkarne/AI-Powered-Github-Repo-Analyzer | 중 | 중 | FastAPI + React + OpenAI. GitHub profile/repo metrics, README quality, chart UI |
| `projects/janwilmake__chat-for-github` | https://github.com/janwilmake/chat-for-github | 낮음 | 중상 | Cloudflare Worker 단일 파일 구조. 여러 repo chat, AI file read/tool execution 아이디어 참고 |
| `projects/vstorm-co__full-stack-ai-agent-template` | https://github.com/vstorm-co/full-stack-ai-agent-template | 높음 | 높음 | FastAPI + Next.js + RAG + streaming + auth + Celery/Docker/K8s 템플릿 |
| `projects/google-gemini__gemini-fullstack-langgraph-quickstart` | https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart | 중상 | 높음 | React + LangGraph/FastAPI agent 흐름. 검색, reflection, citation 생성 패턴 참고 |

## 프론트엔드 디자인 관점 추천

| 우선순위 | 레퍼런스 | 참고 포인트 |
| ---: | --- | --- |
| 1 | `403errors__repomind` | 제품형 랜딩, repo search, chat interface, file preview, architecture map, streaming status |
| 2 | `HarishChandran3304__TTG` | GitHub repo 입력 후 바로 대화하는 단순하고 직관적인 flow |
| 3 | `chroma-core__github-sync-demo` | Next.js 기반 chat with code UX, 추천 질문, code-oriented landing |
| 4 | `CraftFossLabs__chatrepos.ai` | ChatGPT 스타일의 깔끔한 conversational UI |
| 5 | `MatheusAFD__repo-lens` | 모노레포 UI 시스템, e2e 테스트가 있는 portal 구조 |
| 6 | `CronusL-1141__repo-insight` | 분석 진행률, report view, ECharts heatmap 같은 분석 대시보드 UI |

## 백엔드/RAG 로직 관점 추천

| 우선순위 | 레퍼런스 | 참고 포인트 |
| ---: | --- | --- |
| 1 | `Manas2412__CodeBase-Q-A-with-RAG` | AST-aware chunking, pgvector, HyDE, reranker, Redis cache, SSE streaming |
| 2 | `Neverdecel__CodeRAG` | chunking/retrieval/store/surface 모듈 분리, 테스트 구조 |
| 3 | `amrgaberM__CodeBase-Intelligence` | hybrid retrieval, dependency graph, reranking, query expansion, evaluator |
| 4 | `CronusL-1141__repo-insight` | multi-agent planner, guardrail, timeout fallback, WebSocket progress |
| 5 | `wende__cicada` | AST indexing, call-site/dependency tracking, token-efficient code context |
| 6 | `kvnpetit__structured-repo-context-mcp` | MCP tool interface, tree-sitter + LanceDB, local embedding |

## CodeCompass에 적용할 만한 설계 조합

가장 현실적인 MVP 조합:

```text
TTG의 GitHub URL 입력 UX
+ CodeBase-Q-A-with-RAG의 AST/RAG pipeline
+ RepoMind의 온보딩 리포트/파일 트리/streaming progress UI
+ RepoInsight의 WebSocket progress와 분석 단계 표시
```

## MVP 기능 제안

1. Public GitHub URL 입력
2. Repository metadata, README, file tree 수집
3. 중요 파일 선별
4. 파일 타입별 chunking
5. embedding 저장
6. 프로젝트 요약 생성
7. 처음 읽을 파일 Top 10 추천
8. 실행 방법 추론
9. repo 기반 Q&A
10. 답변마다 source path 표시

## 큰 레포 대응 전략

- 전체 파일을 LLM에 한 번에 넣지 않는다.
- file tree와 설정 파일은 전체 맥락으로 사용한다.
- 코드 전문은 함수/클래스/컴포넌트 단위로 쪼개서 RAG 검색 대상으로 저장한다.
- 질문 시 반드시 `repo_id` 기준으로 검색 범위를 제한한다.
- MVP에서는 파일 수, 파일 크기, 확장자를 제한한다.

추천 제한값:

```text
max_files: 50~100
max_file_size: 100KB
exclude: node_modules, .git, dist, build, .venv, lock-only large files, images, binaries
priority: README, package config, backend entrypoint, routers, models, services, frontend pages/components
```

## 레퍼런스 사용 시 주의

- 이 폴더의 프로젝트들은 참고용 스냅샷입니다.
- 각 프로젝트의 라이선스와 원본 README를 확인한 뒤 필요한 아이디어만 설계에 반영합니다.
- 소스 코드를 그대로 복사해 제품 코드에 붙이지 않습니다.
- 실제 API key, `.env`, secret, token은 포함하지 않습니다.
