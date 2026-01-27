from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment


class Certificate(TimestampMixin, Base):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    serial_no: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    certificate_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    issued_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    enrollment: Mapped["Enrollment"] = relationship("Enrollment", backref="certificates")
