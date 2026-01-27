"""
Tests for enrollment prerequisite validation.
"""
import pytest
from uuid import uuid4


class TestEnrollmentPrerequisites:
    """Test prerequisite validation for enrollments."""

    def test_enroll_without_prerequisites_succeeds(
        self, client, auth_headers, basic_course
    ):
        """Student can enroll in course with no prerequisites."""
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(basic_course.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["course_id"] == str(basic_course.id)
        assert data["status"] == "active"

    def test_enroll_with_completed_prerequisites_succeeds(
        self, client, auth_headers, advanced_course, completed_enrollment
    ):
        """Student can enroll in course after completing prerequisites."""
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(advanced_course.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["course_id"] == str(advanced_course.id)

    def test_enroll_without_completed_prerequisites_fails(
        self, client, auth_headers, advanced_course
    ):
        """Student cannot enroll without completing prerequisites."""
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(advanced_course.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        
        # Check that response mentions prerequisites
        detail = data["detail"]
        if isinstance(detail, dict):
            assert "missing_prerequisites" in detail
            assert len(detail["missing_prerequisites"]) > 0
            assert detail["missing_prerequisites"][0]["title"] == "Python Basics"
        else:
            assert "prerequisite" in str(detail).lower()

    def test_enroll_with_active_not_completed_prerequisites_fails(
        self, client, auth_headers, advanced_course, student_user, basic_course, db
    ):
        """Student cannot enroll if prerequisites are in progress but not completed."""
        from app.modules.enrollments.models import Enrollment, EnrollmentStatus
        from datetime import datetime
        
        # Create active (not completed) enrollment in prerequisite course
        active_enrollment = Enrollment(
            id=uuid4(),
            user_id=student_user.id,
            course_id=basic_course.id,
            status=EnrollmentStatus.active,
            enrolled_at=datetime.utcnow()
        )
        db.add(active_enrollment)
        db.commit()
        
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(advanced_course.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 400

    def test_enroll_archived_course_fails(
        self, client, auth_headers, basic_course, db
    ):
        """Cannot enroll in archived course."""
        from app.modules.courses.models import CourseStatus
        
        # Archive the course
        basic_course.status = CourseStatus.archived
        db.commit()
        
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(basic_course.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "archived" in response.json()["detail"].lower()

    def test_idempotent_enrollment(
        self, client, auth_headers, basic_course
    ):
        """Enrolling twice returns the same enrollment."""
        # First enrollment
        response1 = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(basic_course.id)},
            headers=auth_headers
        )
        enrollment_id_1 = response1.json()["id"]
        
        # Second enrollment (should return same)
        response2 = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(basic_course.id)},
            headers=auth_headers
        )
        enrollment_id_2 = response2.json()["id"]
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        assert enrollment_id_1 == enrollment_id_2


"""
Tests for enrollment limit validation.
"""
import pytest
from uuid import uuid4
from datetime import datetime


class TestEnrollmentLimits:
    """Test enrollment limit (max_students) validation."""

    def test_enroll_within_limit_succeeds(
        self, client, auth_headers, advanced_course, completed_enrollment
    ):
        """Can enroll when course is not full."""
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(advanced_course.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 201

    def test_enroll_at_limit_fails(
        self, client, db, advanced_course, completed_enrollment, student_role, auth_headers
    ):
        """Cannot enroll when course is at max capacity."""
        from app.modules.auth.models import User, UserRole
        from app.modules.enrollments.models import Enrollment, EnrollmentStatus
        from app.core.security import get_password_hash
        
        # Course has max_students=3
        # Create 3 enrollments to fill it
        for i in range(3):
            student = User(
                id=uuid4(),
                email=f"student{i}@test.com",
                password_hash=get_password_hash("password123"),
                full_name=f"Student {i}"
            )
            db.add(student)
            db.flush()
            
            user_role = UserRole(user_id=student.id, role_id=student_role.id)
            db.add(user_role)
            
            enrollment = Enrollment(
                id=uuid4(),
                user_id=student.id,
                course_id=advanced_course.id,
                status=EnrollmentStatus.active,
                enrolled_at=datetime.utcnow()
            )
            db.add(enrollment)
        
        db.commit()
        
        # Try to enroll 4th student (should fail)
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(advanced_course.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "full" in response.json()["detail"].lower()

    def test_unlimited_course_allows_many_enrollments(
        self, client, db, basic_course, student_role, auth_headers
    ):
        """Course with no limit allows unlimited enrollments."""
        from app.modules.auth.models import User, UserRole
        from app.modules.enrollments.models import Enrollment, EnrollmentStatus
        from app.core.security import get_password_hash
        
        # Create 100 enrollments (basic_course has max_students=None)
        for i in range(100):
            student = User(
                id=uuid4(),
                email=f"student{i}@test.com",
                password_hash=get_password_hash("password123"),
                full_name=f"Student {i}"
            )
            db.add(student)
            db.flush()
            
            user_role = UserRole(user_id=student.id, role_id=student_role.id)
            db.add(user_role)
            
            enrollment = Enrollment(
                id=uuid4(),
                user_id=student.id,
                course_id=basic_course.id,
                status=EnrollmentStatus.active,
                enrolled_at=datetime.utcnow()
            )
            db.add(enrollment)
        
        db.commit()
        
        # Should still allow one more
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(basic_course.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 201

    def test_completed_enrollments_dont_count_toward_limit(
        self, client, db, advanced_course, completed_enrollment, student_role, auth_headers
    ):
        """Completed enrollments don't count toward active limit."""
        from app.modules.auth.models import User, UserRole
        from app.modules.enrollments.models import Enrollment, EnrollmentStatus
        from app.core.security import get_password_hash
        from datetime import timedelta
        
        # Create 3 COMPLETED enrollments (shouldn't block)
        for i in range(3):
            student = User(
                id=uuid4(),
                email=f"completed{i}@test.com",
                password_hash=get_password_hash("password123"),
                full_name=f"Completed Student {i}"
            )
            db.add(student)
            db.flush()
            
            user_role = UserRole(user_id=student.id, role_id=student_role.id)
            db.add(user_role)
            
            enrollment = Enrollment(
                id=uuid4(),
                user_id=student.id,
                course_id=advanced_course.id,
                status=EnrollmentStatus.completed,
                enrolled_at=datetime.utcnow() - timedelta(days=30),
                completed_at=datetime.utcnow() - timedelta(days=1)
            )
            db.add(enrollment)
        
        db.commit()
        
        # Should still allow enrollment (completed don't count)
        response = client.post(
            "/api/v1/enrollments",
            json={"course_id": str(advanced_course.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 201

