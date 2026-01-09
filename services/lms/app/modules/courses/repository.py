from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.courses.models import Course, Module, LearningAsset, CourseStatus


class CourseRepository:
    """Repository for Course entity with CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, course_id: uuid.UUID) -> Optional[Course]:
        """Get course by ID."""
        return self.db.query(Course).filter(Course.id == course_id).first()

    def list_all(self, status_filter: Optional[CourseStatus] = None) -> list[Course]:
        """List all courses with optional status filter."""
        query = self.db.query(Course)
        if status_filter:
            query = query.filter(Course.status == status_filter)
        return query.order_by(Course.created_at.desc()).all()

    def list_published(self) -> list[Course]:
        """List only published courses."""
        return self.list_all(status_filter=CourseStatus.published)

    def create(
        self,
        title: str,
        description: Optional[str] = None,
        status: CourseStatus = CourseStatus.draft,
        instructor_id: Optional[uuid.UUID] = None,
    ) -> Course:
        """Create a new course."""
        course = Course(
            title=title,
            description=description,
            status=status,
            instructor_id=instructor_id,
        )
        self.db.add(course)
        self.db.flush()
        return course

    def update(self, course: Course, **kwargs) -> Course:
        """Update course fields."""
        for key, value in kwargs.items():
            if hasattr(course, key):
                setattr(course, key, value)
        self.db.flush()
        return course

    def delete(self, course: Course) -> None:
        """Delete course."""
        self.db.delete(course)
        self.db.flush()


class ModuleRepository:
    """Repository for Module entity with CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, module_id: uuid.UUID) -> Optional[Module]:
        """Get module by ID."""
        return self.db.query(Module).filter(Module.id == module_id).first()

    def list_by_course(self, course_id: uuid.UUID) -> list[Module]:
        """List all modules for a course."""
        return (
            self.db.query(Module)
            .filter(Module.course_id == course_id)
            .order_by(Module.order_index.asc())
            .all()
        )

    def create(
        self,
        course_id: uuid.UUID,
        title: str,
        description: Optional[str] = None,
        order_index: int = 1,
    ) -> Module:
        """Create a new module."""
        module = Module(
            course_id=course_id,
            title=title,
            description=description,
            order_index=order_index,
        )
        self.db.add(module)
        self.db.flush()
        return module

    def update(self, module: Module, **kwargs) -> Module:
        """Update module fields."""
        for key, value in kwargs.items():
            if hasattr(module, key):
                setattr(module, key, value)
        self.db.flush()
        return module

    def delete(self, module: Module) -> None:
        """Delete module."""
        self.db.delete(module)
        self.db.flush()


class LearningAssetRepository:
    """Repository for LearningAsset entity with CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, asset_id: uuid.UUID) -> Optional[LearningAsset]:
        """Get learning asset by ID."""
        return self.db.query(LearningAsset).filter(LearningAsset.id == asset_id).first()

    def list_by_module(self, module_id: uuid.UUID) -> list[LearningAsset]:
        """List all learning assets for a module."""
        return (
            self.db.query(LearningAsset)
            .filter(LearningAsset.module_id == module_id)
            .order_by(LearningAsset.order_index.asc())
            .all()
        )

    def create(self, **kwargs) -> LearningAsset:
        """Create a new learning asset."""
        asset = LearningAsset(**kwargs)
        self.db.add(asset)
        self.db.flush()
        return asset

    def update(self, asset: LearningAsset, **kwargs) -> LearningAsset:
        """Update learning asset fields."""
        for key, value in kwargs.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        self.db.flush()
        return asset

    def delete(self, asset: LearningAsset) -> None:
        """Delete learning asset."""
        self.db.delete(asset)
        self.db.flush()
