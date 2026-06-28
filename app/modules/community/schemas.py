from pydantic import BaseModel

class CreateCommunityRequest(BaseModel):
    name: str

class CommunityResponse(BaseModel):
    id: str
    name: str
