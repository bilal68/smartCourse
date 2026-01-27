"""Tests for enrollment authentication and authorization."""

import pytest
from uuid import uuid4
from datetime import datetime

from app.modules.auth.models import User, Role, UserRole
from app.modules.courses.models import Course, CourseStatus
from app.modules.enrollments.models import Enrollment, EnrollmentStatus
from app.core.security import get_password_hash


class TestEnrollmentAuthPermissions:
    """Test authentication and role-based access control for enrollments."""

    def test_student_can_enroll_themselves(
        self, client, db, basic_course, student_user, auth_headers
    ):
        """Students can enroll themselves without providing user_id."""
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(basic_course.id)},
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(student_user.id)
        assert data["course_id"] == str(basic_course.id)

    def test_student_cannot_enroll_others(
        self, client, db, basic_course, student_user, student_role, auth_headers
    ):
        """Students cannot enroll other users."""
        # Create another student
        other_student = User(
            id=uuid4(),
            email="other@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Other Student"
        )
        db.add(other_student)
        db.flush()
        
        user_role = UserRole(user_id=other_student.id, role_id=student_role.id)
        db.add(user_role)
        db.commit()
        
        # Try to enroll the other student
        response = client.post(
            "/api/v1/enrollments",
            json={
                "course_id": str(basic_course.id),
                "user_id": str(other_student.id)
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 403
        assert "only enroll yourself" in response.json()["detail"].lower()

    def test_instructor_can_enroll_others(
        self, client, db, basic_course, student_role, instructor_role
    ):
        """Instructors can enroll other users."""
        from app.core.security import create_access_token
        
        # Create instructor
        instructor = User(
            id=uuid4(),
            email="instructor2@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Instructor User"
        )
        db.add(instructor)
        db.flush()
        
        instructor_user_role = UserRole(user_id=instructor.id, role_id=instructor_role.id)
        db.add(instructor_user_role)
        db.commit()
        
        # Create student to enroll
        student = User(
            id=uuid4(),
            email="student@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Student User"
        )
        db.add(student)
        db.flush()
        
        student_user_role = UserRole(user_id=student.id, role_id=student_role.id)
        db.add(student_user_role)
        db.commit()
        
        # Instructor enrolls the student
        token = create_access_token(subject=str(instructor.id))
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post(
            "/api/v1/enrollments",
            json={
                "course_id": str(basic_course.id),
                "user_id": str(student.id)
            },
            headers=headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(student.id)

    def test_admin_can_enroll_others(
        self, client, db, basic_course, student_role, admin_role
    ):
        """Admins can enroll other users."""
        from app.core.security import create_access_token
        
        # Create admin
        admin = User(
            id=uuid4(),
            email="admin2@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Admin User"
        )
        db.add(admin)
        db.flush()
        
        admin_user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
        db.add(admin_user_role)
        db.commit()
        
        # Create student to enroll
        student = User(
            id=uuid4(),
            email="student@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Student User"
        )
        db.add(student)
        db.flush()
        
        student_user_role = UserRole(user_id=student.id, role_id=student_role.id)
        db.add(student_user_role)
        db.commit()
        
        # Admin enrolls the student
        token = create_access_token(subject=str(admin.id))
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post(
            "/api/v1/enrollments",
            json={
                "course_id": str(basic_course.id),
                "user_id": str(student.id)
            },
            headers=headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(student.id)

    def test_student_can_view_own_enrollments(
        self, client, db, basic_course, student_user, auth_headers
    ):
        """Students can view their own enrollments."""
        # Create enrollment
        enrollment = Enrollment(
            id=uuid4(),
            user_id=student_user.id,
            course_id=basic_course.id,
            status=EnrollmentStatus.active,
            enrolled_at=datetime.utcnow()
        )
        db.add(enrollment)
        db.commit()
        
        # Get my enrollments
        response = client.get(
            "/api/v1/enrollments/me",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(enrollment.id)

    def test_student_cannot_view_others_enrollments(
        self, client, db, basic_course, student_user, student_role, auth_headers
    ):
        """Students cannot view other users' enrollments."""
        # Create another student with enrollment
        other_student = User(
            id=uuid4(),
            email="other@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Other Student"
        )
        db.add(other_student)
        db.flush()
        
        user_role = UserRole(user_id=other_student.id, role_id=student_role.id)
        db.add(user_role)
        db.commit()
        
        # Try to view other student's enrollments
        response = client.get(
            f"/api/v1/enrollments/by-user/{other_student.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    def test_student_can_update_own_enrollment(
        self, client, db, basic_course, student_user, auth_headers
    ):
        """Students can update their own enrollments."""
        # Create enrollment
        enrollment = Enrollment(
            id=uuid4(),
            user_id=student_user.id,
            course_id=basic_course.id,
            status=EnrollmentStatus.active,
            enrolled_at=datetime.utcnow()
        )
        db.add(enrollment)
        db.commit()
        
        # Update enrollment
        response = client.patch(
            f"/api/v1/enrollments/{enrollment.id}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_student_cannot_update_others_enrollment(
        self, client, db, basic_course, student_user, student_role, auth_headers
    ):
        """Students cannot update other users' enrollments."""
        # Create another student with enrollment
        other_student = User(
            id=uuid4(),
            email="other@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Other Student"
        )
        db.add(other_student)
        db.flush()
        
        user_role = UserRole(user_id=other_student.id, role_id=student_role.id)
        db.add(user_role)
        
        other_enrollment = Enrollment(
            id=uuid4(),
            user_id=other_student.id,
            course_id=basic_course.id,
            status=EnrollmentStatus.active,
            enrolled_at=datetime.utcnow()
        )
        db.add(other_enrollment)
        db.commit()
        
        # Try to update other's enrollment
        response = client.patch(
            f"/api/v1/enrollments/{other_enrollment.id}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        
        assert response.status_code == 403

    def test_student_can_delete_own_enrollment(
        self, client, db, basic_course, student_user, auth_headers
    ):
        """Students can delete their own enrollments."""
        # Create enrollment
        enrollment = Enrollment(
            id=uuid4(),
            user_id=student_user.id,
            course_id=basic_course.id,
            status=EnrollmentStatus.active,
            enrolled_at=datetime.utcnow()
        )
        db.add(enrollment)
        db.commit()
        
        # Delete enrollment
        response = client.delete(
            f"/api/v1/enrollments/{enrollment.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 204

    def test_student_cannot_delete_others_enrollment(
        self, client, db, basic_course, student_user, student_role, auth_headers
    ):
        """Students cannot delete other users' enrollments."""
        # Create another student with enrollment
        other_student = User(
            id=uuid4(),
            email="other@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Other Student"
        )
        db.add(other_student)
        db.flush()
        
        user_role = UserRole(user_id=other_student.id, role_id=student_role.id)
        db.add(user_role)
        
        other_enrollment = Enrollment(
            id=uuid4(),
            user_id=other_student.id,
            course_id=basic_course.id,
            status=EnrollmentStatus.active,
            enrolled_at=datetime.utcnow()
        )
        db.add(other_enrollment)
        db.commit()
        
        # Try to delete other's enrollment
        response = client.delete(
            f"/api/v1/enrollments/{other_enrollment.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 403
