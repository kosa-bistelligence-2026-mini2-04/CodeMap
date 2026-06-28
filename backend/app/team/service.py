import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.auth.models import TeamMember
from app.repo.models import AnalysisJob

class TeamService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def transfer_orphan_ownership(self, user_id: uuid.UUID) -> None:
        """
        사용자 탈퇴 시, 해당 사용자가 생성한 팀 공유 분석 이력(team job)의 소유권을
        같은 팀 내 합류순 최선임 활성 멤버에게 자동 양도(벌크 업데이트)합니다.
        """
        # 사용자가 작성한 팀 잡이 있는지 확인
        stmt = select(AnalysisJob.team_id).where(
            AnalysisJob.user_id == user_id,
            AnalysisJob.team_id.is_not(None)
        ).distinct()

        result = await self.db.execute(stmt)
        team_ids = result.scalars().all()

        for t_id in team_ids:
            # 해당 팀의 다른 활성 멤버 중 joined_at이 가장 빠른 멤버 찾기
            member_stmt = select(TeamMember.user_id).where(
                TeamMember.team_id == t_id,
                TeamMember.user_id != user_id,
                TeamMember.status == "active"
            ).order_by(TeamMember.created_at.asc()).limit(1)

            member_res = await self.db.execute(member_stmt)
            next_owner_id = member_res.scalar_one_or_none()

            if next_owner_id:
                # 소유권 양도
                update_stmt = update(AnalysisJob).where(
                    AnalysisJob.team_id == t_id,
                    AnalysisJob.user_id == user_id
                ).values(user_id=next_owner_id)
                await self.db.execute(update_stmt)
            else:
                # 다른 멤버가 없으면 user_id를 None으로 만들어 완전히 고아 상태로 처리
                update_stmt = update(AnalysisJob).where(
                    AnalysisJob.team_id == t_id,
                    AnalysisJob.user_id == user_id
                ).values(user_id=None)
                await self.db.execute(update_stmt)
