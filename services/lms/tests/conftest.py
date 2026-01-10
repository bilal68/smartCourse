"""
Pytest configuration and fixtures for testing.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.deps import get_db
from app.core.security import get_password_hash
from app.modules.auth.models import User, Role, UserRole
from app.modules.courses.models import Course, CourseStatus
from app.modules.enrollments.models import Enrollment, EnrollmentStatus
from datetime import datetime, timedelta
from uuid import uuid4


# Test database URL
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client with test database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def student_role(db):
    """Create student role."""
    role = Role(id=uuid4(), name="student")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def instructor_role(db):
    """Create instructor role."""
    role = Role(id=uuid4(), name="instructor")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def admin_role(db):
    """Create admin role."""
    role = Role(id=uuid4(), name="admin")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def student_user(db, student_role):
    """Create a student user."""
    user = User(
        id=uuid4(),
        email="student@test.com",
        password_hash=get_password_hash("password123"),
        full_name="Test Student"
    )
    db.add(user)
    db.flush()
    
    user_role = UserRole(user_id=user.id, role_id=student_role.id)
    db.add(user_role)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def instructor_user(db, instructor_role):
    """Create an instructor user."""
    user = User(
        id=uuid4(),
        email="instructor@test.com",
        password_hash=get_password_hash("password123"),
        full_name="Test Instructor"
    )
    db.add(user)
    db.flush()
    
    user_role = UserRole(user_id=user.id, role_id=instructor_role.id)
    db.add(user_role)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def basic_course(db, instructor_user):
    """Create a basic course without prerequisites."""
    course = Course(
        id=uuid4(),
        title="Python Basics",
        description="Introduction to Python",
        status=CourseStatus.published,
        instructor_id=instructor_user.id,
        max_students=None
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture
def advanced_course(db, instructor_user, basic_course):
    """Create an advanced course with prerequisites."""
    course = Course(
        id=uuid4(),
        title="Advanced Python",
        description="Deep dive into Python",
        status=CourseStatus.published,
        instructor_id=instructor_user.id,
        max_students=3
    )
    db.add(course)
    db.flush()
    
    # Add prerequisite
    course.prerequisites.append(basic_course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture
def completed_enrollment(db, student_user, basic_course):
    """Create a completed enrollment."""
    enrollment = Enrollment(
        id=uuid4(),
        user_id=student_user.id,
        course_id=basic_course.id,
        status=EnrollmentStatus.completed,
        enrolled_at=datetime.utcnow() - timedelta(days=30),
        completed_at=datetime.utcnow() - timedelta(days=15)
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@pytest.fixture
def auth_headers(client, student_user):
    """Get authentication headers for student user."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": student_user.email,
            "password": "password123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
