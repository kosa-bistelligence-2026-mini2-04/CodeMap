# Current Work

## 2026-06-26 — PR #169 UI/UX audit issue sync

- Current branch: `codex/issue-docs-spec-sync`
- Current goal: Keep PR #169 as the documentation hub for issue-driven product/spec updates.
- Current status:
  - Created non-overlapping follow-up issues #174-#181 from the project-wide UI/UX and logic audit.
  - Excluded areas already covered by #156-#173, including chat scroll/evidence/attachments, Repository preview/line jump, analyze mock charts, Windows local upload, and team/private sharing.
  - Updated product specs so #174-#181 have traceable feature IDs and API/error contracts before implementation begins.
- Files touched or likely relevant:
  - `docs/01_Overview/FUNCTIONAL_SPECIFICATION.md`
  - `docs/02_Architecture/ARCHITECTURE.md`
  - `docs/03_Specifications/01_Project/spec/PROJECT_AUTH_SPEC.md`
  - `docs/03_Specifications/01_Project/spec/PROJECT_ANALYZE_SPEC.md`
  - `docs/03_Specifications/01_Project/spec/PROJECT_CORE_SPEC.md`
  - `docs/03_Specifications/01_Project/spec/PROJECT_LIST_SPEC.md`
  - `docs/03_Specifications/01_Project/api/PROJECT_LIST_API_SPEC.md`
  - `docs/03_Specifications/01_Project/api/PROJECT_REPO_API_SPEC.md`
  - `docs/03_Specifications/03_LLM/api/LLM_COMMON_API_SPEC.md`
  - `docs/03_Specifications/ERROR_CODES.md`
  - `docs/04_Decisions/ERROR_HANDLING.md`
- Validation:
  - `rg`로 Issue #174-#181과 신규 기능 ID가 문서에 연결되는지 확인.
  - `python3`로 Phase 2 기능 인덱스 53개 행 카운트 확인.
  - `git diff --check` 통과.
- Known issues:
  - Existing untracked files `backend/run_analysis.py`, `backend/seed.py`, `backend/test_chat.py` are unrelated and must not be staged for PR #169.
- Next steps:
  - Commit, push, and update PR #169 body with #174-#181 mappings.

## 2026-06-25 — Phase 1 run stream UI hardening

- Current branch: `feat/phase1-agent-run-hardening`
- Current goal: Finish oosuhada Phase 1 tasks from PR #126 follow-up: frontend stream event handling and real-repo run dogfooding.
- Current status:
  - Added a shared frontend stream-event timeline formatter for `worker_started`, `worker_result`, `evidence_compacted`, `references`, `completed`, `failed`, and `cancelled`.
  - Updated `ChatInterface` to append every handled run event to the exploration timeline and to surface failed/cancelled terminal states cleanly.
  - Fixed Planner fallback so missing or invalid OpenAI credentials do not prevent Phase 1 run graph execution.
  - Fixed Planner LLM factory to pass the configured API key explicitly.
  - Dogfooded a real CodeMap repo question: "Run stream 이벤트 타입은 프론트 어디에서 처리돼?"
- Files touched or likely relevant:
  - `frontend/src/features/chat/api/chatApi.ts`
  - `frontend/src/features/chat/components/ChatInterface.tsx`
  - `backend/app/agent/nodes/dispatcher_node.py`
  - `backend/app/agent/nodes/planner_node.py`
  - `backend/app/agent/llm_client.py`
  - `backend/tests/unit/test_agent.py`
  - `backend/tests/unit/test_chat_issue_56.py`
- Commands run:
  - `env -u GITHUB_TOKEN /opt/homebrew/bin/gh auth status`
  - `env -u GITHUB_TOKEN /opt/homebrew/bin/gh api repos/kosa-bistelligence-2026-mini2-04/CodeMap/issues/comments/4797727054`
  - `PATH=".../node/bin:.../bin:$PATH" ./node_modules/.bin/eslint src/features/chat/api/chatApi.ts src/features/chat/components/ChatInterface.tsx`
  - `backend/.venv/bin/python - <<'PY' ... CodeMapAgentService dogfood ... PY`
- Validation:
  - `backend/tests/unit`: 159 passed, 5 skipped with test-only PostgreSQL-form `DATABASE_URL`, `JWT_SECRET_KEY`, and `OPENAI_API_KEY`.
  - Focused LLM/chat tests: 20 passed.
  - `compileall` for `backend/app/agent`, `backend/app/chat`, and `backend/app/tool` passed.
  - `eslint src/features/chat/api/chatApi.ts src/features/chat/components/ChatInterface.tsx` passed.
  - `next build --webpack` passed. Turbopack build was not used because the worktree borrows `node_modules` through a symlink and Turbopack rejects symlinks outside the project root.
  - `git diff --check` passed.
  - Spec/code grep confirmed stream events in `LLM_COMMON_API_SPEC.md`, `LLM_CHAT_RUN_API_SPEC.md`, frontend stream types, and HTTP examples.
- Dogfooding result:
  - Actual repo agent stream emitted `planner_plan`, `route_validated`, `worker_started`, `worker_result`, `evidence_compacted`, and `internal_state`.
  - Evidence collection returned 5 items with sample paths including `frontend/src/features/chat/api/chatApi.ts` and `frontend/src/features/chat/components/ChatInterface.tsx`.
  - `compact_context` was populated.
- Known issues:
  - Dogfood used test-only invalid OpenAI/DB values, so Planner used the fallback path and semantic search fell back after DB connection refusal. File-based evidence still verified the stream/evidence contract.
- Next steps:
  - Push branch and open a PR after final reviewer-risk pass.

## 2026-06-25 — Phase 2 evaluator decision and re-plan timeline

- Current branch: `feat/phase2-evaluator-replan-loop`
- Current goal: Finish oosuhada Phase 2 tasks from PR #126 follow-up: Evaluator judge prompt/schema and frontend timeline events.
- Current status:
  - Added `EvaluatorDecision` state shape with `sufficient`, `missingInfo`, `nextPlanHint`, `reason`, and `confidence`.
  - Added Evaluator judge schema/prompt builder and `create_evaluator_llm()` factory.
  - Updated `evaluator_node` to emit `evaluator_decision`; it emits `replan_started` when fallback judgment says evidence is insufficient and the retry limit allows another pass.
  - Added the LangGraph conditional edge that routes Evaluator back to Planner until `max_replans` is reached.
  - Updated chat stream types and `ChatInterface` to show `evaluator_decision` and `replan_started` in the exploration timeline.
  - Updated LLM Evaluator, Agent, Chat, and Common API specs to include the Phase 2 event contract.
- Validation:
  - `backend/tests/unit`: 162 passed, 5 skipped with test-only PostgreSQL-form `DATABASE_URL`, `JWT_SECRET_KEY`, and `OPENAI_API_KEY`.
  - `backend/.venv/bin/python -m compileall -q backend/app/agent backend/app/chat backend/app/tool` passed
  - `eslint src/features/chat/api/chatApi.ts src/features/chat/components/ChatInterface.tsx` passed
  - `next build --webpack` passed. Turbopack build was not used because the worktree borrows `node_modules` through a symlink and Turbopack rejects symlinks outside the project root.
  - `git diff --check` passed
  - Spec/code comparison for `evaluator_decision`, `replan_started`, `sufficient`, `missingInfo`, and `nextPlanHint` passed
  - Real repo dogfood emitted `evaluator_decision` twice, emitted `replan_started` once, and recorded `compact_context.evaluatorDecision`
- Files touched or likely relevant:
  - `backend/app/agent/state.py`
  - `backend/app/agent/llm_client.py`
  - `backend/app/agent/nodes/evaluator_node.py`
  - `backend/app/agent/service.py`
  - `backend/tests/unit/test_agent.py`
  - `backend/tests/unit/test_chat_issue_56.py`
  - `frontend/src/features/chat/api/chatApi.ts`
  - `frontend/src/features/chat/components/ChatInterface.tsx`
  - `docs/03_Specifications/03_LLM/**`
- Known issues:
  - The current loop is intentionally capped at one re-plan pass by default (`max_replans=1`) to keep Phase 2 review scope bounded.
- Next steps:
  - Push branch and open a Draft PR after final reviewer-risk pass.

## 2026-06-25 — Run registry and Phase 1 stream contract alignment

- Current branch: `refactor/split-core-to-infra-common`
- Current goal: Move the implementation toward the Phase 1 agent/run contract instead of documenting temporary gaps.
- Current status:
  - Preserved `AGENT_GRAPH_FLOW.md` as a Phase 1 target diagram and restored `worker_started` in the worker sequence.
  - Added a shared chat run registry so run create, stream, status, evidence, and cancel operate on the same run record.
  - Replaced run management 501 stubs with registry-backed status/evidence/cancel responses.
  - Added `worker_started` events from worker adapters and wired the frontend stream handler to display them.
  - Updated LLM specs/API docs to treat Run create, Run stream, status, evidence, cancel, references, and worker_started as implemented Phase 1 contracts.
- Validation:
  - Pending for this change set.

## 2026-06-25 — Agent spec implementation-contract cleanup

- Current branch: `refactor/split-core-to-infra-common`
- Current goal: Align current implementation contracts with the latest Planner -> Dispatcher -> Workers -> Evaluator architecture, excluding `AGENT_GRAPH_FLOW.md` because it visualizes the Phase 1 completion target.
- Current status:
  - Split current SSE events from planned future events in the common/chat LLM specs.
  - Documented the current Run stream event contract after removing the legacy chat bridge (`POST /api/chat/{repo_id}`).
  - Updated Dispatcher and tool security descriptions to match current `_ALLOWED_EXTENSIONS` and `Path.relative_to()` behavior.
  - Removed the unused `backend/app/agent/workers/workers.py` compatibility export.
  - Reworded the external tool service as an MCP-style interface while it remains a 501 Phase 2 stub.
- Validation:
  - `backend/.venv/bin/python -m pytest backend/tests/unit -v --tb=short` — `160 passed, 5 skipped`
  - `backend/.venv/bin/python -m compileall -q backend/app/agent backend/app/tool backend/app/chat` passed
  - `git diff --check` passed

## 2026-06-25 — PR #126 agent architecture realignment

- Current branch: `refactor/split-core-to-infra-common`
- Current goal: Adopt the Planner -> Dispatcher -> Tool Workers -> Evaluator architecture and align code/docs/specs with that decision.
- Current status:
  - Added `backend/app/agent/llm_client.py` as the LLM provider/factory boundary.
  - Added `backend/app/agent/nodes/` for `planner_node`, `dispatcher_node`, and `evaluator_node`.
  - Removed legacy worker import wrappers after code/tests/docs migrated to the new node modules.
  - Split deterministic tool implementations into `backend/app/tool/dir_scan.py`, `grep_scan.py`, and `file_read.py`.
  - Reworked `search_worker`, `dir_worker`, `grep_worker`, and `read_worker` as worker adapters around search/tool logic.
  - Updated architecture/spec/API docs to use Planner/Dispatcher/Workers/Evaluator terminology and mark reasoning worker behavior as Phase 2 optional.
- Files touched or likely relevant:
  - `backend/app/agent/llm_client.py`
  - `backend/app/agent/graph.py`
  - `backend/app/agent/nodes/*`
  - `backend/app/agent/workers/*`
  - `backend/app/tool/dir_scan.py`
  - `backend/app/tool/grep_scan.py`
  - `backend/app/tool/file_read.py`
  - `backend/app/chat/final_answer_agent.py`
  - `backend/tests/unit/test_agent.py`
  - `backend/tests/unit/test_chat_issue_56.py`
  - `docs/01_Overview/FUNCTIONAL_SPECIFICATION.md`
  - `docs/02_Architecture/*`
  - `docs/03_Specifications/03_LLM/*`
  - `docs/03_Specifications/PHASE2_API_SPEC.md`
  - `docs/04_Decisions/MULTI_AGENT_ARCHITECTURE_DECISION.md`
- Commands run:
  - `rg -n "supervisor_agent|route_node|evidence_aggregator|..."`
  - `backend/.venv/bin/python -m pytest backend/tests/unit -v --tb=short`
  - `git diff --check`
  - `backend/.venv/bin/python -m compileall -q backend/app/agent backend/app/tool backend/app/chat`
- Validation:
  - `160 passed, 5 skipped`
  - `git diff --check` passed
  - compileall passed for agent/tool/chat modules
- Known issues:
  - `route_validated` SSE event name remains intentionally unchanged for frontend compatibility.
  - `backend/app/pipeline/graph.py` contains the analysis pipeline (previously at `backend/app/repo/pipeline/`). It references `route_node_fun` as a separate repository-analysis pipeline concept, not the LLM agent dispatcher.
- Next steps:
  - Ask for an additional PR #126 review against the latest cleanup commit.

## 2026-06-25 — PR #126 migration follow-up

- Current branch: `refactor/split-core-to-infra-common`
- Current goal: Apply the post-migration follow-up plan from PR #126 on top of `bc2b29a`.
- Current status:
  - Added `fanout_to_workers` runtime allowlist for `search`, `dir`, `grep`, `read`.
  - Converted `/tools/execute` to a single Pydantic JSON body and explicit `501`/`failed` response.
  - Removed dummy `success` tool service responses.
  - Added SSE `event:` headers while preserving `data:` JSON lines for the existing frontend stream parser.
  - Cleaned worker stubs, common service placeholder, HTTP test naming, and AGENT-to-LLM/core-to-infra documentation drift.
- Files touched or likely relevant:
  - `backend/app/agent/nodes/dispatcher_node.py`
  - `backend/app/tool/router.py`
  - `backend/app/tool/service.py`
  - `backend/app/chat/router.py`
  - `backend/tests/unit/test_agent.py`
  - `backend/tests/unit/test_tool_router.py`
  - `backend/tests/http/LLM-*`
  - `docs/01_Overview/FUNCTIONAL_SPECIFICATION.md`
  - `docs/02_Architecture/ARCHITECTURE.md`
  - `docs/03_Specifications/PHASE2_API_SPEC.md`
  - `docs/03_Specifications/ERROR_CODES.md`
- Commands run:
  - `env -u GITHUB_TOKEN gh auth status`
  - `env -u GITHUB_TOKEN gh pr view 126 ...`
  - `env -u GITHUB_TOKEN gh api graphql ...`
  - `git pull --rebase`
  - `backend/.venv/bin/python -m pytest backend/tests/unit -v --tb=short`
  - `git diff --check`
  - `rg -n 'AGENT-CHAT|AGENT-SEARCH|AGENT-CORE' backend/tests/http`
  - `rg -n 'AGENT_RUN_' docs`
  - `rg -n 'agent_graph' docs`
  - `rg -n 'core/config' docs | rg -v 'infra'`
- Validation:
  - `157 passed, 5 skipped`
  - `git diff --check` passed
  - Targeted residual string checks returned 0 matches
- Known issues:
  - `AGENT_STREAM_FAILED`, `AGENT_EVIDENCE_*`, and related internal agent error codes remain intentionally unchanged per PR follow-up guidance.
  - Frontend still uses a manual fetch stream parser that reads `data:` lines; the added `event:` header is ignored safely by that parser.
- Next steps:
  - Review the committed diff on PR #126.
  - If the team wants native `EventSource.addEventListener()` handling later, add frontend listeners by SSE event name.
