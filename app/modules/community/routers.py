from fastapi import APIRouter
from app.modules.community.schemas import CreateCommunityRequest, CommunityResponse

router = APIRouter(prefix="/api/v1/communities", tags=["communities"])

@router.get("")
async def get_communities():
    return []

@router.post("", response_model=CommunityResponse)
async def create_community(request: CreateCommunityRequest):
    return {"id": "1", "name": request.name}

@router.get("/{id}")
async def get_community(id: str):
    return {"id": id, "name": "Test"}

@router.delete("/{id}")
async def delete_community(id: str):
    return {"status": "deleted"}
