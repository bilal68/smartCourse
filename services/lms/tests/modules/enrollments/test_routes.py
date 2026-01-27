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


"""Tests for enrollment validation and error cases."""

import pytest
from uuid import uuid4
from datetime import datetime

from app.modules.auth.models import User
from app.modules.courses.models import Course, CourseStatus
from app.modules.enrollments.models import Enrollment, EnrollmentStatus


class TestEnrollmentValidation:
    """Test enrollment validation and error handling."""

    def test_duplicate_enrollment_returns_existing(
        self, client, db, basic_course, student_user, auth_headers
    ):
        """Creating duplicate enrollment returns existing enrollment (idempotency)."""
        # Create first enrollment
        response1 = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(basic_course.id)},
            headers=auth_headers,
        )
        assert response1.status_code == 201
        enrollment_id = response1.json()["id"]
        
        # Try to create again - should return same enrollment
        response2 = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(basic_course.id)},
            headers=auth_headers,
        )
        assert response2.status_code == 201
        assert response2.json()["id"] == enrollment_id

    def test_enroll_with_invalid_course_id(
        self, client, db, student_user, auth_headers
    ):
        """Enrolling with non-existent course ID returns 404."""
        fake_course_id = uuid4()
        
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(fake_course_id)},
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        assert "course not found" in response.json()["detail"].lower()

    def test_enroll_with_invalid_user_id(
        self, client, db, basic_course, admin_role
    ):
        """Enrolling with non-existent user ID returns 404."""
        from app.core.security import create_access_token
        from app.modules.auth.models import UserRole
        
        # Create admin who can enroll others
        admin = User(
            id=uuid4(),
            email="admin@test.com",
            password_hash="hash",
            full_name="Admin"
        )
        db.add(admin)
        db.flush()
        
        admin_user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
        db.add(admin_user_role)
        db.commit()
        
        token = create_access_token(subject=str(admin.id))
        headers = {"Authorization": f"Bearer {token}"}
        
        fake_user_id = uuid4()
        
        response = client.post(
            "/api/v1/enrollments",
            json={
                "course_id": str(basic_course.id),
                "user_id": str(fake_user_id)
            },
            headers=headers,
        )
        
        assert response.status_code == 404
        assert "user not found" in response.json()["detail"].lower()

    def test_get_nonexistent_enrollment(
        self, client, db, auth_headers
    ):
        """Getting non-existent enrollment returns 404."""
        fake_enrollment_id = uuid4()
        
        response = client.get(
            f"/api/v1/enrollments/{fake_enrollment_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        assert "enrollment not found" in response.json()["detail"].lower()

    def test_update_nonexistent_enrollment(
        self, client, db, auth_headers
    ):
        """Updating non-existent enrollment returns 404."""
        fake_enrollment_id = uuid4()
        
        response = client.patch(
            f"/api/v1/enrollments/{fake_enrollment_id}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        assert "enrollment not found" in response.json()["detail"].lower()

    def test_delete_nonexistent_enrollment(
        self, client, db, auth_headers
    ):
        """Deleting non-existent enrollment returns 404."""
        fake_enrollment_id = uuid4()
        
        response = client.delete(
            f"/api/v1/enrollments/{fake_enrollment_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        assert "enrollment not found" in response.json()["detail"].lower()

    def test_enrollment_status_can_be_updated(
        self, client, db, basic_course, student_user, auth_headers
    ):
        """Enrollment status can be updated from active to completed."""
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
        
        # Update to completed
        response = client.patch(
            f"/api/v1/enrollments/{enrollment.id}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    def test_list_enrollments_by_nonexistent_course(
        self, client, db, admin_role
    ):
        """Listing enrollments for non-existent course returns 404."""
        from app.core.security import create_access_token
        from app.modules.auth.models import UserRole
        
        # Create admin
        admin = User(
            id=uuid4(),
            email="admin@test.com",
            password_hash="hash",
            full_name="Admin"
        )
        db.add(admin)
        db.flush()
        
        admin_user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
        db.add(admin_user_role)
        db.commit()
        
        token = create_access_token(subject=str(admin.id))
        headers = {"Authorization": f"Bearer {token}"}
        
        fake_course_id = uuid4()
        
        response = client.get(
            f"/api/v1/enrollments/by-course/{fake_course_id}",
            headers=headers,
        )
        
        assert response.status_code == 404
        assert "course not found" in response.json()["detail"].lower()

    def test_enrollment_with_custom_source(
        self, client, db, basic_course, student_user, auth_headers
    ):
        """Enrollment can be created with custom source field."""
        response = client.post(
            "/api/v1/enrollments",
            json={
                "course_id": str(basic_course.id),
                "source": "mobile_app"
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["source"] == "mobile_app"

    def test_enrollment_with_custom_status(
        self, client, db, basic_course, admin_role, student_role
    ):
        """Admin can create enrollment with custom status."""
        from app.core.security import create_access_token
        from app.modules.auth.models import UserRole
        
        # Create admin and student
        admin = User(
            id=uuid4(),
            email="admin@test.com",
            password_hash="hash",
            full_name="Admin"
        )
        student = User(
            id=uuid4(),
            email="student@test.com",
            password_hash="hash",
            full_name="Student"
        )
        db.add_all([admin, student])
        db.flush()
        
        admin_user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
        student_user_role = UserRole(user_id=student.id, role_id=student_role.id)
        db.add_all([admin_user_role, student_user_role])
        db.commit()
        
        token = create_access_token(subject=str(admin.id))
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post(
            "/api/v1/enrollments",
            json={
                "course_id": str(basic_course.id),
                "user_id": str(student.id),
                "status": "dropped"
            },
            headers=headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "dropped"

