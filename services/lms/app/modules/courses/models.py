from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Table, Text, DateTime, func, BigInteger
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


class CourseProcessingStatus(str, enum.Enum):
    """Status of content processing after course is published"""
    not_started = "not_started"  # Course published but processing not started
    processing = "processing"    # Currently processing content (chunking, etc.)
    ready = "ready"             # Processing complete, course ready for students
    failed = "failed"           # Processing failed with errors


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

    # Content processing status (tracks async content chunking/indexing)
    processing_status: Mapped[CourseProcessingStatus] = mapped_column(
        Enum(CourseProcessingStatus, name="course_processing_status"),
        server_default=CourseProcessingStatus.not_started.value,
        nullable=False,
    )
    
    # Error message if processing failed
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamp when processing completed (successfully or failed)
    processed_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

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


class AssetStatus(str, enum.Enum):
    """Upload and validation status of asset content"""
    draft = "draft"                    # Just metadata, no content
    upload_pending = "upload_pending"  # Signed URL generated, waiting for upload
    uploaded = "uploaded"              # File in S3, not yet validated
    ready = "ready"                    # Validated and ready for students
    rejected = "rejected"              # Validation failed
    archived = "archived"              # Soft deleted


class ContentFormat(str, enum.Enum):
    """Format of content stored in S3"""
    editor_json = "EDITOR_JSON"        # Rich editor JSON format


class StorageProvider(str, enum.Enum):
    """Storage provider for content"""
    s3 = "S3"
    minio = "MINIO"
    local = "LOCAL"


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

    # actual resource location (S3, CDN, external URL, etc.) - for non-ARTICLE types
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # ordering within the module
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # video/audio length (optional)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # === NEW FIELDS FOR ARTICLE CONTENT UPLOADS ===
    
    # Upload and validation status
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status"),
        server_default=AssetStatus.draft.value,
        nullable=False,
        index=True,
    )

    # Content storage details
    content_format: Mapped[str] = mapped_column(String(50), default="EDITOR_JSON", nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(50), default="S3", nullable=False)
    bucket: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    key: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)

    # Upload validation
    expected_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA256 hex
    
    # Versioning and error tracking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    module: Mapped["Module"] = relationship(
        "Module",
        back_populates="assets",
    )
