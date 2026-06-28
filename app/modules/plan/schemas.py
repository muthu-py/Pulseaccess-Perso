from pydantic import BaseModel

class CreatePlanRequest(BaseModel):
    name: str
    price: float

class UpdatePlanRequest(BaseModel):
    name: str
    price: float

class PlanResponse(BaseModel):
    id: str
    name: str
    price: float
