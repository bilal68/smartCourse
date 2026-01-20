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
# Note: ContentChunk removed - now handled by AI service in smartcourse_ai database
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
    # Note: ContentChunk removed - now handled by AI service
    for model in [
        # ContentChunk,  # DEPRECATED - now handled by AI service
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

    # Courses with prerequisites and enrollment limits
    courses = []
    
    # Basic course - PUBLISHED (for prerequisite testing)
    python_basics = Course(
        id=uuid4(),
        instructor_id=inst1.id,
        title="Python Basics",
        description="Introduction to Python programming - perfect for beginners.",
        status=CourseStatus.published,
        max_students=None,  # unlimited enrollment
    )
    db.add(python_basics)
    courses.append(python_basics)
    
    # DRAFT course - for testing publishing workflow
    machine_learning = Course(
        id=uuid4(),
        instructor_id=inst1.id,
        title="Introduction to Machine Learning",
        description="A comprehensive course covering the fundamentals of machine learning algorithms and applications.",
        status=CourseStatus.draft,  # DRAFT STATUS for testing
        max_students=10,
    )
    db.add(machine_learning)
    courses.append(machine_learning)
    
    # Another DRAFT course - for testing publishing workflow
    fastapi_intro = Course(
        id=uuid4(),
        instructor_id=inst2.id,
        title="FastAPI Introduction",
        description="Learn to build REST APIs with FastAPI - comprehensive hands-on course.",
        status=CourseStatus.draft,  # DRAFT STATUS for testing
        max_students=5,
    )
    db.add(fastapi_intro)
    courses.append(fastapi_intro)
    
    # DRAFT Advanced course - for testing complex workflows
    fullstack_course = Course(
        id=uuid4(),
        instructor_id=inst2.id,
        title="Full-Stack Development with FastAPI",
        description="Build complete applications with modern web technologies - comprehensive project-based learning.",
        status=CourseStatus.draft,  # DRAFT STATUS for testing
        max_students=2,
    )
    db.add(fullstack_course)
    courses.append(fullstack_course)
    
    # One more PUBLISHED course for variety
    data_science = Course(
        id=uuid4(),
        instructor_id=inst1.id,
        title="Data Science Fundamentals",
        description="Learn data analysis, visualization, and basic statistics.",
        status=CourseStatus.published,
        max_students=8,
    )
    db.add(data_science)
    courses.append(data_science)
    
    db.flush()
    
    # Set up prerequisite relationships
    # Full-Stack requires Python Basics (published course as prerequisite)
    fullstack_course.prerequisites.append(python_basics)
    
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

            # Note: ContentChunk creation removed - now handled by AI service when course is published
            # The AI service will process these assets and create chunks in its own database
            
    # Enrollments with prerequisite test scenarios
    now = datetime.utcnow()
    enrollments = []
    
    # Student 1: Completed Python Basics (can enroll in Advanced Python)
    e1 = Enrollment(
        id=uuid4(),
        user_id=students[0].id,
        course_id=python_basics.id,
        status=EnrollmentStatus.completed,
        enrolled_at=now - timedelta(days=30),
        completed_at=now - timedelta(days=15),
    )
    db.add(e1)
    enrollments.append(e1)
    
    # Student 2: Completed Python Basics (can enroll in Advanced Python)
    e2 = Enrollment(
        id=uuid4(),
        user_id=students[1].id,
        course_id=python_basics.id,
        status=EnrollmentStatus.completed,
        enrolled_at=now - timedelta(days=25),
        completed_at=now - timedelta(days=10),
    )
    db.add(e2)
    enrollments.append(e2)
    
    # Student 3: Currently learning Python Basics (cannot enroll in Advanced Python yet)
    e3 = Enrollment(
        id=uuid4(),
        user_id=students[2].id,
        course_id=python_basics.id,
        status=EnrollmentStatus.active,
        enrolled_at=now - timedelta(days=5),
    )
    db.add(e3)
    enrollments.append(e3)
    
    # Student 4: No enrollments (cannot enroll in Advanced Python - missing prerequisite)
    
    # Student 1: Also completed FastAPI Introduction (can enroll in Full-Stack)
    e4 = Enrollment(
        id=uuid4(),
        user_id=students[0].id,
        course_id=fastapi_intro.id,
        status=EnrollmentStatus.completed,
        enrolled_at=now - timedelta(days=20),
        completed_at=now - timedelta(days=5),
    )
    db.add(e4)
    enrollments.append(e4)
    
    # Student 2: Currently learning FastAPI (cannot enroll in Full-Stack yet)
    e5 = Enrollment(
        id=uuid4(),
        user_id=students[1].id,
        course_id=fastapi_intro.id,
        status=EnrollmentStatus.active,
        enrolled_at=now - timedelta(days=3),
    )
    db.add(e5)
    enrollments.append(e5)

    db.flush()

    # create progress and optional certificates
    for e in enrollments:
        # For completed enrollments, set 100% progress
        if e.status == EnrollmentStatus.completed:
            percent = 100.0
        else:
            # For active enrollments, random progress
            percent = random.choice([10.0, 35.0, 60.0])
            
        cp = CourseProgress(
            id=uuid4(),
            enrollment_id=e.id,
            percent_complete=percent,
            started_at=e.enrolled_at,
            completed_at=e.completed_at if e.status == EnrollmentStatus.completed else None,
        )
        db.add(cp)

        if e.status == EnrollmentStatus.completed:
            db.add(Certificate(
                id=uuid4(),
                enrollment_id=e.id,
                serial_no=f"CERT-{uuid4().hex[:10].upper()}",
                certificate_url="https://example.com/demo/cert.pdf",
                issued_at=e.completed_at or now,
            ))

        # optionally add asset-level progress for some assets in the course
        assets = db.query(LearningAsset).filter(LearningAsset.module_id.in_(
            db.query(Module.id).filter(Module.course_id == e.course_id)
        )).all()
        if assets:
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
    print(f"   - Created {len(courses)} courses for testing:")
    print(f"     * '{python_basics.title}' (PUBLISHED - no prerequisites, unlimited)")
    print(f"     * '{machine_learning.title}' (DRAFT - ready to test publishing, max 10 students)")
    print(f"     * '{fastapi_intro.title}' (DRAFT - ready to test publishing, max 5 students)")
    print(f"     * '{fullstack_course.title}' (DRAFT - requires Python Basics, max 2 students)")
    print(f"     * '{data_science.title}' (PUBLISHED - no prerequisites, max 8 students)")
    print(f"   - Created {len(students)} students with test scenarios:")
    print(f"     * student1@smartcourse.dev: Completed Python Basics (can test enrollments)")
    print(f"     * student2@smartcourse.dev: Completed Python Basics (can test enrollments)")
    print(f"     * student3@smartcourse.dev: Learning Python Basics (progress testing)")
    print(f"     * student4@smartcourse.dev: No enrollments (fresh user for testing)")
    print(f"     * student5@smartcourse.dev: No enrollments (fresh user for testing)")
    print("   - 🚀 READY TO TEST: Use draft courses to test complete publishing workflow!")


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
