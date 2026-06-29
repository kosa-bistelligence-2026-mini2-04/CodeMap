from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infra.database import get_db
from app.infra.auth import get_current_user
from app.auth.models import User, Team, TeamMember, TeamInvite
from app.team.schemas import (
    TeamCreate,
    TeamResponse,
    TeamInviteRequest,
    TeamMemberResponse,
    TeamListResponse,
    TeamInviteResponse,
    TeamInviteListItem,
    TeamInviteListResponse,
    AcceptInviteResponse,
    DeclineInviteResponse,
)
import uuid

router = APIRouter(prefix="/api/teams", tags=["Team"])
invite_router = APIRouter(prefix="/api/team-invites", tags=["Team"])


def _current_user_id(current_user: dict) -> uuid.UUID:
    try:
        return uuid.UUID(str(current_user["sub"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user token") from exc


def _current_user_email(current_user: dict) -> str:
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return str(email)


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
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=403, detail="TEAM_ACCESS_DENIED")
    if owner_only and member.role != "owner":
        raise HTTPException(status_code=403, detail="TEAM_OWNER_REQUIRED")
    return member


def _team_response(team: Team, member: TeamMember) -> TeamResponse:
    return TeamResponse(
        id=team.id,
        teamId=team.id,
        name=team.name,
        role=member.role,
        joinedAt=member.created_at,
    )


def _aware(dt: datetime) -> datetime:
    ## DB에서 naive로 돌아오는 경우를 대비해 UTC로 보정 후 비교
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


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


# ──────────────────────────────────────────────
# PROJECT-TEAM-API-003: 팀 초대 생성 (owner만)
# 즉시 멤버를 활성화하지 않고 pending 초대를 생성한다.
# ──────────────────────────────────────────────
@router.post("/{team_id}/invites", response_model=TeamInviteResponse, status_code=201)
async def create_invite(
    team_id: uuid.UUID,
    req: TeamInviteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = _current_user_id(current_user)
    await _require_member(db, team_id, user_id, owner_only=True)

    email = req.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="INVALID_EMAIL")

    ## 이미 active member인 이메일은 재초대 불필요
    existing_member = await db.execute(
        select(TeamMember.id)
        .join(User, User.id == TeamMember.user_id)
        .where(
            TeamMember.team_id == team_id,
            TeamMember.status == "active",
            User.email == email,
        )
    )
    if existing_member.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="TEAM_MEMBER_ALREADY_EXISTS")

    ## 같은 팀/이메일의 pending 초대가 있으면 만료시간만 갱신하여 재사용
    pending = await db.execute(
        select(TeamInvite).where(
            TeamInvite.team_id == team_id,
            TeamInvite.email == email,
            TeamInvite.status == "pending",
        )
    )
    invite = pending.scalar_one_or_none()
    if invite is None:
        invite = TeamInvite(
            team_id=team_id,
            email=email,
            invited_by_user_id=user_id,
            role=req.role,
            status="pending",
        )
        db.add(invite)
    else:
        invite.invited_by_user_id = user_id
        invite.role = req.role
    await db.commit()
    await db.refresh(invite)
    return TeamInviteResponse(
        inviteId=invite.id,
        teamId=invite.team_id,
        email=invite.email,
        status=invite.status,
        expiresAt=invite.expires_at,
    )


# ──────────────────────────────────────────────
# PROJECT-TEAM-API-007: 팀 멤버 목록 조회 (active member만)
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# PROJECT-TEAM-API-004: 내 이메일로 온 pending 초대 목록
# ──────────────────────────────────────────────
@invite_router.get("", response_model=TeamInviteListResponse)
async def list_my_invites(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    email = _current_user_email(current_user).strip().lower()
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(TeamInvite, Team, User)
        .join(Team, Team.id == TeamInvite.team_id)
        .join(User, User.id == TeamInvite.invited_by_user_id, isouter=True)
        .where(TeamInvite.email == email, TeamInvite.status == "pending")
        .order_by(TeamInvite.created_at.desc())
    )
    invites = []
    for invite, team, inviter in result.all():
        if _aware(invite.expires_at) < now:
            continue
        invites.append(
            TeamInviteListItem(
                inviteId=invite.id,
                teamId=invite.team_id,
                teamName=team.name,
                invitedByEmail=inviter.email if inviter else None,
                status=invite.status,
                expiresAt=invite.expires_at,
            )
        )
    return TeamInviteListResponse(invites=invites)


async def _load_invite_for_current_user(
    db: AsyncSession,
    invite_id: uuid.UUID,
    email: str,
) -> TeamInvite:
    result = await db.execute(select(TeamInvite).where(TeamInvite.id == invite_id))
    invite = result.scalar_one_or_none()
    ## 초대 이메일과 로그인 이메일이 일치하지 않으면 존재 자체를 숨긴다.
    if invite is None or invite.email != email:
        raise HTTPException(status_code=404, detail="TEAM_INVITE_NOT_FOUND")
    return invite


# ──────────────────────────────────────────────
# PROJECT-TEAM-API-005: 초대 수락 -> active member 생성
# ──────────────────────────────────────────────
@invite_router.post("/{invite_id}/accept", response_model=AcceptInviteResponse)
async def accept_invite(
    invite_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = _current_user_id(current_user)
    email = _current_user_email(current_user).strip().lower()
    invite = await _load_invite_for_current_user(db, invite_id, email)

    if invite.status != "pending":
        raise HTTPException(status_code=409, detail="TEAM_INVITE_ALREADY_USED")
    if _aware(invite.expires_at) < datetime.now(timezone.utc):
        invite.status = "expired"
        await db.commit()
        raise HTTPException(status_code=409, detail="TEAM_INVITE_EXPIRED")

    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == invite.team_id,
            TeamMember.user_id == user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if member is None:
        member = TeamMember(
            team_id=invite.team_id,
            user_id=user_id,
            role=invite.role or "member",
            status="active",
        )
        db.add(member)
    else:
        member.status = "active"
        if member.role != "owner":
            member.role = invite.role or "member"
    invite.status = "accepted"
    await db.commit()
    await db.refresh(member)
    return AcceptInviteResponse(teamId=invite.team_id, role=member.role)


# ──────────────────────────────────────────────
# PROJECT-TEAM-API-006: 초대 거절
# ──────────────────────────────────────────────
@invite_router.post("/{invite_id}/decline", response_model=DeclineInviteResponse)
async def decline_invite(
    invite_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    email = _current_user_email(current_user).strip().lower()
    invite = await _load_invite_for_current_user(db, invite_id, email)
    if invite.status != "pending":
        raise HTTPException(status_code=409, detail="TEAM_INVITE_ALREADY_USED")
    invite.status = "declined"
    await db.commit()
    return DeclineInviteResponse(inviteId=invite.id, status=invite.status)

# ──────────────────────────────────────────────
# PROJECT-TEAM-API-008: 멤버 제거 (owner만)
# ──────────────────────────────────────────────
@router.delete("/{team_id}/members/{user_id}", response_model=dict)
async def remove_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_id = _current_user_id(current_user)
    await _require_member(db, team_id, current_user_id, owner_only=True)
    if current_user_id == user_id:
        raise HTTPException(status_code=400, detail="CANNOT_REMOVE_SELF")

    target = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    target_member = target.scalar_one_or_none()
    if not target_member or target_member.status != "active":
        raise HTTPException(status_code=404, detail="MEMBER_NOT_FOUND")

    target_member.status = "removed"
    await db.commit()
    return {"message": "removed", "userId": target_member.user_id}


# ──────────────────────────────────────────────
# PROJECT-TEAM-API-009: 팀 탈퇴
# ──────────────────────────────────────────────
@router.post("/{team_id}/leave", response_model=dict)
async def leave_team(
    team_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_id = _current_user_id(current_user)
    member = await _require_member(db, team_id, current_user_id)

    if member.role == "owner":
        # Check if there's another owner
        owners = await db.execute(
            select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.role == "owner", TeamMember.status == "active")
        )
        if len(owners.all()) <= 1:
            raise HTTPException(status_code=400, detail="CANNOT_LEAVE_AS_LAST_OWNER")

    member.status = "removed"
    await db.commit()
    return {"message": "left", "teamId": team_id}


# ──────────────────────────────────────────────
# PROJECT-TEAM-API-010: 보낸 초대 목록 조회
# ──────────────────────────────────────────────
@router.get("/{team_id}/invites", response_model=TeamInviteListResponse)
async def list_team_invites(
    team_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_id = _current_user_id(current_user)
    await _require_member(db, team_id, current_user_id, owner_only=True)

    result = await db.execute(
        select(TeamInvite, Team, User)
        .join(Team, Team.id == TeamInvite.team_id)
        .join(User, User.id == TeamInvite.invited_by_user_id, isouter=True)
        .where(TeamInvite.team_id == team_id, TeamInvite.status == "pending")
        .order_by(TeamInvite.created_at.desc())
    )

    now = datetime.now(timezone.utc)
    invites = []
    for invite, team, inviter in result.all():
        if _aware(invite.expires_at) < now:
            continue
        invites.append(
            TeamInviteListItem(
                inviteId=invite.id,
                teamId=invite.team_id,
                teamName=team.name,
                invitedByEmail=inviter.email if inviter else None,
                status=invite.status,
                expiresAt=invite.expires_at,
            )
        )
    return TeamInviteListResponse(invites=invites)


# ──────────────────────────────────────────────
# PROJECT-TEAM-API-011: 초대 취소 (owner만)
# ──────────────────────────────────────────────
@router.post("/{team_id}/invites/{invite_id}/cancel", response_model=dict)
async def cancel_invite(
    team_id: uuid.UUID,
    invite_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_id = _current_user_id(current_user)
    await _require_member(db, team_id, current_user_id, owner_only=True)

    result = await db.execute(select(TeamInvite).where(TeamInvite.id == invite_id, TeamInvite.team_id == team_id))
    invite = result.scalar_one_or_none()

    if not invite or invite.status != "pending":
        raise HTTPException(status_code=404, detail="INVITE_NOT_FOUND_OR_NOT_PENDING")

    invite.status = "cancelled"
    await db.commit()
    return {"message": "cancelled", "inviteId": invite.id}
