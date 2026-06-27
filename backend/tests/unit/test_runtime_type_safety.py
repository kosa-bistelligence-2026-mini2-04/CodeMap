import pytest
import asyncio
from uuid import uuid4
from pydantic import TypeAdapter, ValidationError

from app.agent.state import CodeMapState
from app.parse.schemas import ParseResult, ParsedFile
from app.chat.run_registry import RunRecord
from langchain_core.messages import HumanMessage


# ──────────────────────────────────────────────
# 1. Type Mismatch 및 Literal 위반 테스트
# ──────────────────────────────────────────────
def test_codemapstate_type_safety():
    """CodeMapState (TypedDict)의 런타임 타입 검증"""
    adapter = TypeAdapter(CodeMapState)

    # 정상 데이터
    valid_data = {
        "repo_id": str(uuid4()),
        "run_id": str(uuid4()),
        "session_id": "sess_1",
        "clone_path": "/tmp/clone",
        "user_query": "What is this?",
        "target_file": None,
        "context_files": [],
        "worker_results": [],
        "search_history": [],
        "compact_context": {},
        "memory_context": {},
        "rewritten_query": "",
        "access_plan": [],
        "security_result": {"approved": [], "rejected": []},
        "current_worker": "",
        "events": [],
        "durations": {},
        "evaluator_decision": {"sufficient": True, "missingInfo": [], "nextPlanHint": "", "confidence": 1.0, "reason": "test"},
        "replan_count": 0,
        "max_replans": 3,
        "replan_hint": "",
        "final_answer": "",
        "_plan_item": {"tool": "search", "path": "test", "query": "test", "scope": "file"},
        "errors": []
    }
    # TypedDict는 TypeAdapter로 validate_python 가능
    parsed = adapter.validate_python(valid_data)
    assert parsed["user_query"] == "What is this?"

    # 의도적 오류: access_plan에 잘못된 타입 삽입
    invalid_data = valid_data.copy()
    invalid_data["access_plan"] = ["This is not an AccessPlanItem"]

    with pytest.raises(ValidationError):
        adapter.validate_python(invalid_data)

def test_parseresult_strict_validation():
    """ParseResult 내장 타입 및 Literal 위반 방어 검증"""
    # 필수 필드 누락 시 에러
    with pytest.raises(ValidationError):
        ParseResult() # type: ignore

    # file_type Literal 위반 에러 ("FILE" 또는 "DIRECTORY"만 허용)
    with pytest.raises(ValidationError):
        ParsedFile(
            path="test/path",
            file_type="INVALID_TYPE", # type: ignore
            depth=1
        )


# ──────────────────────────────────────────────
# 2. 극한 데이터(Payload Too Large / Crash 유발) 테스트
# ──────────────────────────────────────────────
def test_payload_too_large_string():
    """매우 긴 문자열 주입 시 Pydantic의 파싱 정상 동작(거부하지 않고 수용) 및 타입 힌트 유지 확인"""
    large_string = "A" * 10_000_000  # 10MB 크기의 문자열

    parsed = ParsedFile(
        path="huge_file.txt",
        file_type="FILE",
        depth=1,
        content=large_string,
        lines=100000,
        size=10000000
    )
    # 데이터가 들어가긴 하지만, 타입이 str로 정확히 들어갔는지 확인
    assert len(parsed.content) == 10_000_000
    assert parsed.file_type == "FILE"

    # 만약 content에 int가 들어가면 에러가 나야 함
    with pytest.raises(ValidationError):
        ParsedFile(
            path="huge_file.txt",
            file_type="FILE",
            depth=1,
            content=123456789, # type: ignore
            lines=1,
            size=1
        )

def test_deeply_nested_dict():
    """무한 재귀를 유발할 수 있는 악성 깊은 딕셔너리 주입 시 파이썬 엔진 크래시 없이 정상 수용되는지 확인 (Pydantic 코어 안정성)"""
    # 딕셔너리 깊이 2000 생성
    deep_dict = {}
    current = deep_dict
    for _ in range(2000):
        current["nested"] = {}
        current = current["nested"]

    # CodeMapState의 compact_context에 주입 시도
    adapter = TypeAdapter(CodeMapState)

    record_data = {
        "repo_id": str(uuid4()),
        "run_id": str(uuid4()),
        "session_id": "sess_1",
        "clone_path": "/tmp/clone",
        "user_query": "What is this?",
        "target_file": None,
        "worker_results": [],
        "search_history": [],
        "compact_context": deep_dict, # 깊은 재귀 딕셔너리 할당
        "memory_context": {},
        "rewritten_query": "",
        "access_plan": [],
        "security_result": {"approved": [], "rejected": []},
        "current_worker": "",
        "events": [],
        "durations": {},
        "evaluator_decision": {"sufficient": True, "missingInfo": [], "nextPlanHint": "", "confidence": 1.0, "reason": "test"},
        "replan_count": 0,
        "max_replans": 3,
        "replan_hint": "",
        "final_answer": "",
        "_plan_item": {"tool": "search", "path": "test", "query": "test", "scope": "file"},
        "errors": []
    }

    # Pydantic V2(Rust 코어)는 Any/dict 타입에 대해 깊은 재귀 데이터도 크래시(RecursionError) 없이 정상적으로 수용함
    parsed = adapter.validate_python(record_data)
    assert parsed["compact_context"] is not None

def test_large_list_of_objects():
    """요소가 비정상적으로 많은 리스트 주입 시(OOM / 성능 지연 방어)"""
    # 요소 100만 개 (성능 문제로 10만 개로 타협)

    adapter = TypeAdapter(CodeMapState)
    valid_data = {
        "repo_id": str(uuid4()),
        "run_id": str(uuid4()),
        "session_id": "sess_1",
        "clone_path": "/tmp/clone",
        "user_query": "What is this?",
        "target_file": None,
        "worker_results": [{"id": f"res_{i}", "path": None, "lineStart": None, "lineEnd": None, "score": None, "snippet": "foo", "metadata": {}} for i in range(100_000)], # 대용량 리스트
        "search_history": [],
        "compact_context": {},
        "memory_context": {},
        "rewritten_query": "",
        "access_plan": [],
        "security_result": {"approved": [], "rejected": []},
        "current_worker": "",
        "events": [],
        "durations": {},
        "evaluator_decision": {"sufficient": True, "missingInfo": [], "nextPlanHint": "", "confidence": 1.0, "reason": "test"},
        "replan_count": 0,
        "max_replans": 3,
        "replan_hint": "",
        "final_answer": "",
        "_plan_item": {"tool": "search", "path": "test", "query": "test", "scope": "file"},
        "errors": []
    }

    # 파싱 완료되거나 극한 갯수 확인
    parsed = adapter.validate_python(valid_data)
    assert len(parsed["worker_results"]) == 100_000


# ──────────────────────────────────────────────
# 3. 비동기 블로킹 방어(Event Loop Block 예방) 개념의 타임아웃 테스트
# ──────────────────────────────────────────────
def test_async_validation_timeout():
    """거대한 데이터를 Pydantic으로 검증할 때 이벤트 루프를 장시간 막지 않는지 개념적 확인"""
    # 1만 개의 복잡한 객체 리스트
    large_files = [
        {
            "path": f"file_{i}.txt",
            "file_type": "FILE",
            "depth": 1,
            "lines": 10,
            "size": 100
        }
        for i in range(10_000)
    ]

    async def validate_data():
        adapter = TypeAdapter(list[ParsedFile])
        return adapter.validate_python(large_files)

    async def run_test():
        # Validation이 2초 내로 수행되는지 확인 (매우 크면 asyncio.to_thread로 빼야 함을 암시)
        try:
            result = await asyncio.wait_for(validate_data(), timeout=2.0)
            assert len(result) == 10_000
        except asyncio.TimeoutError:
            pytest.fail("Pydantic validation blocked the event loop for too long. Consider asyncio.to_thread.")

    asyncio.run(run_test())
