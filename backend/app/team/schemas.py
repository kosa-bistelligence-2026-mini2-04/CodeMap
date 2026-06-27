from pydantic import BaseModel
import uuid
from datetime import datetime

class TeamCreate(BaseModel):
    name: str

class TeamResponse(BaseModel):
    id: uuid.UUID
    teamId: uuid.UUID
    name: str
    role: str
    joinedAt: datetime | None = None

class TeamInviteRequest(BaseModel):
    email: str
    role: str = "member"

class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    teamId: uuid.UUID
    user_id: uuid.UUID
    userId: uuid.UUID
    email: str
    role: str
    status: str

class TeamListResponse(BaseModel):
    teams: list[TeamResponse]


# ──────────────────────────────────────────────
# 초대 플로우 (PROJECT-TEAM-API-003~006)
# ──────────────────────────────────────────────
class TeamInviteResponse(BaseModel):
    inviteId: uuid.UUID
    teamId: uuid.UUID
    email: str
    status: str
    expiresAt: datetime

class TeamInviteListItem(BaseModel):
    inviteId: uuid.UUID
    teamId: uuid.UUID
    teamName: str
    invitedByEmail: str | None = None
    status: str
    expiresAt: datetime

class TeamInviteListResponse(BaseModel):
    invites: list[TeamInviteListItem]

class AcceptInviteResponse(BaseModel):
    teamId: uuid.UUID
    role: str

class DeclineInviteResponse(BaseModel):
    inviteId: uuid.UUID
    status: str


# ──────────────────────────────────────────────
# G3-A: 팀 운영 응답 스키마
# (PROJECT-TEAM-API-008~011)
# ──────────────────────────────────────────────
class RemoveMemberResponse(BaseModel):
    userId: uuid.UUID
    status: str


class LeaveTeamResponse(BaseModel):
    teamId: uuid.UUID
    status: str


class SentInviteItem(BaseModel):
    inviteId: uuid.UUID
    email: str
    status: str
    expiresAt: datetime
    invitedByEmail: str | None = None


class SentInviteListResponse(BaseModel):
    invites: list[SentInviteItem]


class CancelInviteResponse(BaseModel):
    inviteId: uuid.UUID
    status: str
