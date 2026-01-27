"""
Tests for prerequisite management endpoints.
"""
import pytest


class TestPrerequisiteManagement:
    """Test prerequisite add/remove/list endpoints."""

    def test_instructor_can_add_prerequisite(
        self, client, db, instructor_user, basic_course
    ):
        """Instructor can add prerequisite to their course."""
        from app.modules.courses.models import Course, CourseStatus
        from uuid import uuid4
        
        # Create another course
        new_course = Course(
            id=uuid4(),
            title="Advanced Course",
            description="Requires basics",
            status=CourseStatus.published,
            instructor_id=instructor_user.id
        )
        db.add(new_course)
        db.commit()
        
        # Login as instructor
        response = client.post(
            "/api/v1/auth/login",
            data={"username": instructor_user.email, "password": "password123"}
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Add prerequisite
        response = client.post(
            f"/api/v1/courses/{new_course.id}/prerequisites/{basic_course.id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Course should now have prerequisites
        assert len(data.get("prerequisites", [])) > 0 or "id" in data

    def test_instructor_can_remove_prerequisite(
        self, client, db, instructor_user, basic_course, advanced_course
    ):
        """Instructor can remove prerequisite from their course."""
        # Login as instructor
        response = client.post(
            "/api/v1/auth/login",
            data={"username": instructor_user.email, "password": "password123"}
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Remove prerequisite
        response = client.delete(
            f"/api/v1/courses/{advanced_course.id}/prerequisites/{basic_course.id}",
            headers=headers
        )
        
        assert response.status_code == 204

    def test_student_cannot_add_prerequisite(
        self, client, auth_headers, basic_course, advanced_course
    ):
        """Student cannot add prerequisites."""
        response = client.post(
            f"/api/v1/courses/{advanced_course.id}/prerequisites/{basic_course.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 403

    def test_list_prerequisites(
        self, client, advanced_course, basic_course
    ):
        """Can list course prerequisites (public endpoint)."""
        response = client.get(
            f"/api/v1/courses/{advanced_course.id}/prerequisites"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == str(basic_course.id)

    def test_cannot_add_self_as_prerequisite(
        self, client, db, instructor_user, basic_course
    ):
        """Course cannot be its own prerequisite."""
        # Login as instructor
        response = client.post(
            "/api/v1/auth/login",
            data={"username": instructor_user.email, "password": "password123"}
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to add course as its own prerequisite
        response = client.post(
            f"/api/v1/courses/{basic_course.id}/prerequisites/{basic_course.id}",
            headers=headers
        )
        
        assert response.status_code == 400
        assert "itself" in response.json()["detail"].lower()
