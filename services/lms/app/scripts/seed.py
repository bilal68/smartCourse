from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import get_password_hash

from app.modules.auth.models import User, Role, UserRole
from app.modules.courses.models import Course, CourseStatus, Module, LearningAsset, AssetType
from app.modules.enrollments.models import Enrollment, EnrollmentStatus
from app.modules.progress.models import CourseProgress, AssetProgress
from app.models.certificate import Certificate
from app.models.content_chunk import ContentChunk
from app.db.mixins import TimestampMixin

ROLE_ADMIN = "admin"
ROLE_INSTRUCTOR = "instructor"
ROLE_STUDENT = "student"


def get_or_create_role(db: Session, name: str) -> Role:
    role = db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
    if role:
        return role
    role = Role(id=uuid4(), name=name)
    db.add(role)
    return role


def get_or_create_user(db: Session, email: str, password: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        return user
    user = User(
        id=uuid4(),
        email=email,
        password_hash=get_password_hash(password),
        full_name=email.split("@")[0].replace('.', ' ').title(),
    )
    db.add(user)
    return user


def ensure_user_role(db: Session, user_id, role_id) -> None:
    link = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    ).scalar_one_or_none()
    if link:
        return
    db.add(UserRole(user_id=user_id, role_id=role_id))


def reset_data(db: Session) -> None:
    # Adjust order to avoid FK violations
    for model in [
        ContentChunk,
        AssetProgress,
        Certificate,
        CourseProgress,
        Enrollment,
        LearningAsset,
        Module,
        Course,
        UserRole,
        Role,
        User,
    ]:
        db.execute(delete(model))
    db.commit()


def seed(db: Session) -> None:
    # Roles
    r_admin = get_or_create_role(db, ROLE_ADMIN)
    r_inst = get_or_create_role(db, ROLE_INSTRUCTOR)
    r_student = get_or_create_role(db, ROLE_STUDENT)
    db.flush()

    # Users
    admin = get_or_create_user(db, "admin@smartcourse.dev", "Admin123!")
    inst1 = get_or_create_user(db, "instructor1@smartcourse.dev", "Instructor123!")
    inst2 = get_or_create_user(db, "instructor2@smartcourse.dev", "Instructor123!")
    students = [get_or_create_user(db, f"student{i}@smartcourse.dev", "Student123!") for i in range(1, 6)]
    db.flush()

    ensure_user_role(db, admin.id, r_admin.id)
    ensure_user_role(db, inst1.id, r_inst.id)
    ensure_user_role(db, inst2.id, r_inst.id)
    for s in students:
        ensure_user_role(db, s.id, r_student.id)
    db.flush()

    # Courses
    courses = []
    for owner, title in [
        (inst1, "Python for Busy Developers"),
        (inst2, "FastAPI + PostgreSQL Bootcamp"),
    ]:
        c = Course(
            id=uuid4(),
            instructor_id=owner.id,
            title=title,
            description=f"{title} — seeded demo course.",
            status=CourseStatus.published,
        )
        db.add(c)
        courses.append(c)
    db.flush()

    # Modules + Assets
    for c in courses:
        modules = []
        for idx, mt in enumerate(["Getting Started", "Core Concepts", "Project"], start=1):
            m = Module(
                id=uuid4(),
                course_id=c.id,
                title=mt,
                order_index=idx,
            )
            db.add(m)
            modules.append(m)

        db.flush()

        for m in modules:
            # article asset (text-like)
            text = LearningAsset(
                id=uuid4(),
                module_id=m.id,
                asset_type=AssetType.article,
                title=f"{m.title} - Reading",
                source_url=None,
                description=f"Seeded content for {c.title} / {m.title}.",
            )

            video = LearningAsset(
                id=uuid4(),
                module_id=m.id,
                asset_type=AssetType.video,
                title=f"{m.title} - Video",
                source_url="https://example.com/demo/video.mp4",
            )

            pdf = LearningAsset(
                id=uuid4(),
                module_id=m.id,
                asset_type=AssetType.pdf,
                title=f"{m.title} - Notes (PDF)",
                source_url="https://example.com/demo/notes.pdf",
            )

            db.add_all([text, video, pdf])
            db.flush()

            # create content chunks for text/article asset
            db.add_all([
                ContentChunk(id=uuid4(), asset_id=text.id, chunk_index=1, chunk_text="Chunk 1: goals", token_count=3, extra={}, created_at=datetime.utcnow()),
                ContentChunk(id=uuid4(), asset_id=text.id, chunk_index=2, chunk_text="Chunk 2: concepts", token_count=3, extra={}, created_at=datetime.utcnow()),
                ContentChunk(id=uuid4(), asset_id=text.id, chunk_index=3, chunk_text="Chunk 3: examples", token_count=3, extra={}, created_at=datetime.utcnow()),
            ])
            db.flush()

    # Enrollments
    now = datetime.utcnow()
    enrollments = []
    for s in students:
        c = random.choice(courses)
        e = Enrollment(
            id=uuid4(),
            user_id=s.id,
            course_id=c.id,
            status=EnrollmentStatus.active,
            enrolled_at=now - timedelta(days=random.randint(1, 14)),
        )
        db.add(e)
        enrollments.append(e)

    db.flush()

    # create progress and optional certificates
    for e in enrollments:
        percent = random.choice([10.0, 35.0, 60.0, 100.0])
        cp = CourseProgress(
            id=uuid4(),
            enrollment_id=e.id,
            percent_complete=percent,
            started_at=e.enrolled_at,
            completed_at=now if percent == 100.0 else None,
        )
        db.add(cp)

        if percent == 100.0:
            e.status = EnrollmentStatus.completed
            e.completed_at = now
            db.add(Certificate(
                id=uuid4(),
                enrollment_id=e.id,
                serial_no=f"CERT-{uuid4().hex[:10].upper()}",
                certificate_url="https://example.com/demo/cert.pdf",
                issued_at=now,
            ))

        # optionally add asset-level progress for some assets in the course
        assets = db.query(LearningAsset).filter(LearningAsset.module_id.in_(
            db.query(Module.id).filter(Module.course_id == e.course_id)
        )).all()
        for a in random.sample(assets, k=min(len(assets), random.randint(0, 2))):
            ap = AssetProgress(
                id=uuid4(),
                asset_id=a.id,
                enrollment_id=e.id,
                percent_complete=random.choice([0.0, 25.0, 50.0, 100.0]),
                started_at=e.enrolled_at,
                completed_at=now if random.choice([False, True]) else None,
            )
            db.add(ap)

    db.commit()
    print("✅ Seed completed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.reset:
            reset_data(db)
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
