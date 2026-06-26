from pydantic import BaseModel
import uuid

class TeamCreate(BaseModel):
    name: str

class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    
class TeamInvite(BaseModel):
    email: str
    role: str = "member"

class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: str
