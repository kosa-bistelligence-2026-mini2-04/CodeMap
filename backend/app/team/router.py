from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.database import get_db
from app.infra.auth import get_current_user
from app.auth.models import User, Team, TeamMember
from app.team.schemas import TeamCreate, TeamResponse, TeamInvite, TeamMemberResponse
import uuid

router = APIRouter(prefix="/api/team", tags=["Team"])

@router.post("", response_model=TeamResponse)
async def create_team(
    req: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    team = Team(name=req.name)
    db.add(team)
    await db.flush()
    
    member = TeamMember(team_id=team.id, user_id=current_user.id, role="owner")
    db.add(member)
    await db.commit()
    
    return TeamResponse(id=team.id, name=team.name)

@router.post("/{team_id}/invite", response_model=TeamMemberResponse)
async def invite_member(
    team_id: uuid.UUID,
    req: TeamInvite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Mock implementation for Phase 4
    raise HTTPException(status_code=501, detail="Not implemented yet")
