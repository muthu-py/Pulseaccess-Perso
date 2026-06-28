import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class NotificationLog(Base):
    __tablename__ = "notification_log"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID]
    message_type: Mapped[str]
