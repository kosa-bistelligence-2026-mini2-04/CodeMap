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
