from pydantic import BaseModel

class CreatePlanRequest(BaseModel):
    name: str
    price: float
    duration_days: int = 30

class UpdatePlanRequest(BaseModel):
    name: str
    price: float
    duration_days: int = 30

class PlanResponse(BaseModel):
    id: str
    name: str
    price: float
    duration_days: int
