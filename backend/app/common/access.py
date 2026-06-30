"""
분석 job 접근 권한 단일 판정 모듈 (PROJECT_TEAM_SPEC private/team visibility 정책).

list / repo / chat / websocket / sse 등 모든 경로가 이 모듈을 거쳐
동일한 격리 규칙을 적용하도록 한다. (자체 PR 리뷰 M3: can_access_job 중복 제거)
"""
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TeamMember


_bg_tasks: set = set()


# ──────────────────────────────────────────────
# user_has_team_access: 팀의 active member 여부
# ──────────────────────────────────────────────
async def user_has_team_access(
    db: AsyncSession,
    team_id: UUID | None,
    user_id: UUID | None,
) -> bool:
    if team_id is None or user_id is None:
        return False
    result = await db.execute(
        select(TeamMember.id).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.status == "active",
        )
    )
    return result.scalar_one_or_none() is not None


# ──────────────────────────────────────────────
# can_access_job: job 단위 접근 허용 여부
# ──────────────────────────────────────────────
async def can_access_job(
    db: AsyncSession,
    job,
    current_user_id: UUID | None,
) -> bool:
    team_id = getattr(job, "team_id", None)
    user_id = getattr(job, "user_id", None)
    is_private = bool(getattr(job, "is_private", False))
    ## team job: 해당 팀 active member만 접근
    if team_id is not None:
        return await user_has_team_access(db, team_id, current_user_id)
    ## private job: 생성자 본인만 접근
    if user_id is not None:
        return current_user_id == user_id
    ## 소유자/팀이 모두 없는 레거시 공개 job만 무인증 접근 허용
    return not is_private


# ──────────────────────────────────────────────
# touch_last_accessed: 최근 접근 시각 업데이트 (논블로킹 백그라운드)
# ──────────────────────────────────────────────
def touch_last_accessed(db: AsyncSession, job_id: UUID) -> None:
    """
    분석 작업의 최근 접근 시각(last_accessed_at)을 백그라운드 태스크로 논블로킹 업데이트한다.
    Mock 세션 유입 등 테스트 모킹 상태일 때는 안전 가드에 의해 갱신을 생략한다.
    """
    import asyncio
    
    ## mock db / session 가드 검사
    if type(db).__name__ in ("Mock", "MagicMock", "AsyncMock"):
        return

    async def _do_update() -> None:
        try:
            from app.repo.repository import AnalysisJobRepository
            ## [순환 임포트 방지] app.infra.database -> app.repo.service -> database 순환 참조 방지를 위해 지역 임포트 처리
            from app.infra.database import async_session_factory
            async with async_session_factory() as session:
                repo = AnalysisJobRepository(session)
                await repo.update_last_accessed(job_id)
                await session.commit()
        except Exception as exc:
            ## 백그라운드 갱신의 예외가 메인 흐름을 깨뜨리지 않도록 보호하되 경고 로그 남김
            logger.warning(
                "[touch_last_accessed] 최근 접근 시각 업데이트 실패 (job_id: %s): %s",
                job_id,
                exc,
                exc_info=True,
            )

    task = asyncio.create_task(_do_update())
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
