from fastapi import APIRouter

router = APIRouter(tags=["members"])

@router.get("/api/v1/communities/{id}/members")
async def get_members(id: str):
    return []
