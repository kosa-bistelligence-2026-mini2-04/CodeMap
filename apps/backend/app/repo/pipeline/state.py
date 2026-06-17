"""
분석 파이프라인 LangGraph 공유 상태 정의

# [Sec09 - LangGraph 공유 상태]
# kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/state.py 참고
#
# ShareState TypedDict를 CodeMap 분석 파이프라인에 맞게 적용했다.
# 각 노드는 PipelineState를 입력으로 받고, 처리 결과를 dict로 반환하여 상태를 갱신한다.
# str 타입으로 처리했지만 실제 서비스 연동 시 Pydantic 모델로 교체하면 더 좋다.
"""

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


# [Sec09 - ShareState] 파이프라인 전 노드가 공유하는 상태 정의
# messages 필드는 add_messages Reducer로 각 Agent 응답이 자동 누적된다.
class PipelineState(TypedDict):
    """
    CodeMap 분석 파이프라인 전 구간에 걸쳐 공유되는 상태

    # [Sec09 - ShareState]
    # kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/state.py 참고
    # messages는 add_messages를 사용해 기존 메시지 목록에 새 메시지를 누적할 수 있다.
    """

    # [Sec09 - add_messages] LangChain 메시지 히스토리
    # 각 Agent의 응답이 누적되어 다음 노드에서 컨텍스트로 활용된다.
    messages: Annotated[list[dict[str, Any]], add_messages]

    # 분석 작업 식별자
    job_id: str

    # GitHub 저장소 메타데이터
    repo_url: str
    branch: str
    owner: str
    repo_name: str

    # Clone 결과 경로 (clone_node 완료 후 설정, start_pipeline 재시작 시 미리 설정됨)
    clone_path: Optional[str]

    # 파이프라인 진행 상태
    current_stage: str
    progress: int
    status: str

    # 오류 메시지 (실패 시 설정)
    error: Optional[str]
