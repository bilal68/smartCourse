from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.module import Module


class AssetType(str, enum.Enum):
    video = "video"
    pdf = "pdf"
    article = "article"
    link = "link"
    quiz = "quiz"
    other = "other"


class LearningAsset(TimestampMixin, Base):
    __tablename__ = "learning_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type"),
        server_default=AssetType.other.value,
        nullable=False,
    )

    # actual resource location (S3, CDN, external URL, etc.)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # ordering within the module
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # video/audio length (optional)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    module: Mapped["Module"] = relationship(
        "Module",
        back_populates="assets",
    )
