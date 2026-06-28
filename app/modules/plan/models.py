import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID]
    name: Mapped[str]
    price: Mapped[float]
