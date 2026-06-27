"""
분석 job 접근 권한 단일 판정 모듈 (PROJECT_TEAM_SPEC private/team visibility 정책).

list / repo / chat / websocket / sse 등 모든 경로가 이 모듈을 거쳐
동일한 격리 규칙을 적용하도록 한다. (자체 PR 리뷰 M3: can_access_job 중복 제거)
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TeamMember


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
