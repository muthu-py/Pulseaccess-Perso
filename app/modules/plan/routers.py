from fastapi import APIRouter
from app.modules.plan.schemas import CreatePlanRequest, UpdatePlanRequest, PlanResponse

router = APIRouter(tags=["plans"])

@router.get("/api/v1/communities/{id}/plans")
async def get_plans(id: str):
    return []

@router.post("/api/v1/communities/{id}/plans", response_model=PlanResponse)
async def create_plan(id: str, request: CreatePlanRequest):
    return {"id": "1", "name": request.name, "price": request.price}

@router.put("/api/v1/plans/{id}", response_model=PlanResponse)
async def update_plan(id: str, request: UpdatePlanRequest):
    return {"id": id, "name": request.name, "price": request.price}

@router.delete("/api/v1/plans/{id}")
async def delete_plan(id: str):
    return {"status": "deleted"}
