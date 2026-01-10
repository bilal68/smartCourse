from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Table, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.enrollments.models import Enrollment


# Association table for course prerequisites (many-to-many)
course_prerequisites = Table(
    'course_prerequisites',
    Base.metadata,
    Column('course_id', UUID(as_uuid=True), ForeignKey('courses.id', ondelete='CASCADE'), primary_key=True),
    Column('prerequisite_course_id', UUID(as_uuid=True), ForeignKey('courses.id', ondelete='CASCADE'), primary_key=True),
    Column('is_mandatory', Boolean, default=True, nullable=False),
    Column('created_at', DateTime, server_default=func.now(), nullable=False),
)


class CourseStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus, name="course_status"),
        server_default=CourseStatus.draft.value,
        nullable=False,
    )

    # NEW: Maximum number of students allowed (NULL = unlimited)
    max_students: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # optional: instructor "owns" the course
    instructor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    instructor: Mapped["User | None"] = relationship(
        "User",
        back_populates="courses_created",
        foreign_keys=[instructor_id],
    )

    modules: Mapped[list["Module"]] = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="course",
        cascade="all, delete-orphan",
    )

    # NEW: Prerequisites relationship (courses that must be completed before this one)
    prerequisites: Mapped[list["Course"]] = relationship(
        "Course",
        secondary=course_prerequisites,
        primaryjoin=id == course_prerequisites.c.course_id,
        secondaryjoin=id == course_prerequisites.c.prerequisite_course_id,
        backref="is_prerequisite_for",
    )


class Module(TimestampMixin, Base):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    course: Mapped["Course"] = relationship(
        "Course",
        back_populates="modules",
    )

    assets: Mapped[list["LearningAsset"]] = relationship(
        "LearningAsset",
        back_populates="module",
        cascade="all, delete-orphan",
    )


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
