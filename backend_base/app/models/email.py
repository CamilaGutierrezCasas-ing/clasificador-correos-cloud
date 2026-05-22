from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Float, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    linked_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("linked_accounts.id"),
        nullable=True,
        index=True,
    )

    graph_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        unique=True,
    )

    original_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    was_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sender: Mapped[str] = mapped_column(String(255), nullable=False, default="desconocido")
    source_account: Mapped[str] = mapped_column(String(255), nullable=False, default="local-demo")
    predicted_category: Mapped[str] = mapped_column(String(50), nullable=False, default="otros")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_synced_from_microsoft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User")
    linked_account = relationship("LinkedAccount")
