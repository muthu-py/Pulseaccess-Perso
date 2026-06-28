import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class Community(Base):
    __tablename__ = "communities"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    creator_id: Mapped[uuid.UUID]
    name: Mapped[str]
    telegram_channel_id: Mapped[str]
