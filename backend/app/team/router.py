from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infra.database import get_db
from app.infra.auth import get_current_user
from app.auth.models import User, Team, TeamMember
from app.team.schemas import TeamCreate, TeamResponse, TeamInvite, TeamMemberResponse, TeamListResponse
import uuid

router = APIRouter(prefix="/api/teams", tags=["Team"])


def _current_user_id(current_user: dict) -> uuid.UUID:
    try:
        return uuid.UUID(str(current_user["sub"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user token") from exc


async def _require_member(
    db: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    owner_only: bool = False,
) -> TeamMember:
    stmt = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
        TeamMember.status == "active",
    )
    if owner_only:
        stmt = stmt.where(TeamMember.role == "owner")
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=403, detail="TEAM_ACCESS_DENIED")
    return member


def _team_response(team: Team, member: TeamMember) -> TeamResponse:
    return TeamResponse(
        id=team.id,
        teamId=team.id,
        name=team.name,
        role=member.role,
        joinedAt=member.created_at,
    )

@router.post("", response_model=TeamResponse)
async def create_team(
    req: TeamCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = _current_user_id(current_user)
    team = Team(name=req.name, created_by_user_id=user_id)
    db.add(team)
    await db.flush()
    
    member = TeamMember(team_id=team.id, user_id=user_id, role="owner", status="active")
    db.add(member)
    await db.commit()
    await db.refresh(team)
    await db.refresh(member)
    
    return _team_response(team, member)

@router.get("", response_model=TeamListResponse)
async def list_teams(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = _current_user_id(current_user)
    result = await db.execute(
        select(Team, TeamMember)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user_id, TeamMember.status == "active")
        .order_by(Team.created_at.desc())
    )
    return TeamListResponse(
        teams=[_team_response(team, member) for team, member in result.all()]
    )


@router.post("/{team_id}/invite", response_model=TeamMemberResponse)
async def invite_member(
    team_id: uuid.UUID,
    req: TeamInvite,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = _current_user_id(current_user)
    await _require_member(db, team_id, user_id, owner_only=True)

    user_result = await db.execute(select(User).where(User.email == req.email))
    invited_user = user_result.scalar_one_or_none()
    if invited_user is None:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == invited_user.id,
        )
    )
    member = member_result.scalar_one_or_none()
    if member is None:
        member = TeamMember(
            team_id=team_id,
            user_id=invited_user.id,
            role=req.role,
            status="active",
        )
        db.add(member)
    else:
        member.role = req.role
        member.status = "active"
    await db.commit()
    await db.refresh(member)
    return TeamMemberResponse(
        id=member.id,
        team_id=member.team_id,
        teamId=member.team_id,
        user_id=member.user_id,
        userId=member.user_id,
        email=invited_user.email,
        role=member.role,
        status=member.status,
    )


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def list_members(
    team_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = _current_user_id(current_user)
    await _require_member(db, team_id, user_id)
    result = await db.execute(
        select(TeamMember, User)
        .join(User, User.id == TeamMember.user_id)
        .where(TeamMember.team_id == team_id, TeamMember.status == "active")
        .order_by(TeamMember.created_at.asc())
    )
    return [
        TeamMemberResponse(
            id=member.id,
            team_id=member.team_id,
            teamId=member.team_id,
            user_id=member.user_id,
            userId=member.user_id,
            email=user.email,
            role=member.role,
            status=member.status,
        )
        for member, user in result.all()
    ]
