# Codebase Onboarding Reference Projects

CodeCompass 2차 프로젝트 주제인 "AI 코드베이스 온보딩 도우미"를 설계할 때 참고하기 위한 오픈소스 레퍼런스 모음입니다.

## 폴더 구성

```text
references/codebase-onboarding/
├── README.md
├── REFERENCE_COMPARISON.md
└── projects/
    ├── 403errors__repomind/
    ├── HarishChandran3304__TTG/
    ├── Manas2412__CodeBase-Q-A-with-RAG/
    └── ...
```

## 스냅샷 원칙

- 각 프로젝트는 GitHub 원본을 참고용 소스 스냅샷으로 복사했습니다.
- 개별 프로젝트의 `.git`, `node_modules`, `.venv`, `dist`, `build`, `.next` 등 무거운 산출물은 제외했습니다.
- 실행용 의존성은 포함하지 않았으므로, 실제 실행이 필요하면 각 프로젝트 README에 맞춰 별도로 설치해야 합니다.
- 레퍼런스 코드는 제품 코드에 직접 병합하지 말고, 구조/UX/RAG 파이프라인 설계 참고용으로만 사용합니다.

## 먼저 볼 순서

1. `projects/403errors__repomind`
   - 제품형 UI, repo search, chat, architecture map, security scan, streaming progress 참고
2. `projects/HarishChandran3304__TTG`
   - GitHub URL 입력 후 repo chat으로 이어지는 가장 직접적인 풀스택 참고
3. `projects/Manas2412__CodeBase-Q-A-with-RAG`
   - tree-sitter chunking, pgvector, HyDE, reranking, SSE streaming 등 RAG 백엔드 참고
4. `projects/Neverdecel__CodeRAG`
   - 코드베이스 RAG 라이브러리 구조, chunking/retrieval/store/API 분리 참고
5. `projects/CronusL-1141__repo-insight`
   - multi-agent 분석, WebSocket progress, guardrail, timeout fallback 참고

자세한 비교표는 `REFERENCE_COMPARISON.md`를 확인하세요.
