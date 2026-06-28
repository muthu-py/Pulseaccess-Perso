import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class Member(Base):
    __tablename__ = "members"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID]
    telegram_user_id: Mapped[str]
