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
    
class TeamInvite(BaseModel):
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
