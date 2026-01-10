"""Tests for course service business logic."""

import pytest
from uuid import uuid4
from datetime import datetime

from app.modules.auth.models import User, Role, UserRole
from app.modules.courses.models import Course, CourseStatus, Module
from app.modules.courses.service import CourseService
from app.core.security import get_password_hash


class TestCourseCreation:
    """Test course creation business logic."""

    def test_instructor_can_create_course(self, db, instructor_user):
        """Instructors can create courses."""
        service = CourseService(db)
        
        course = service.create_course(
            title="New Course",
            description="Test description",
            course_status=CourseStatus.draft,
            instructor_id=None,
            user=instructor_user
        )
        
        assert course.title == "New Course"
        assert course.instructor_id == instructor_user.id
        assert course.status == CourseStatus.draft

    def test_admin_can_create_course(self, db, admin_role):
        """Admins can create courses."""
        admin = User(
            id=uuid4(),
            email="admin@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Admin User"
        )
        db.add(admin)
        db.flush()
        
        user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()
        db.refresh(admin)
        
        service = CourseService(db)
        
        course = service.create_course(
            title="Admin Course",
            description="Created by admin",
            course_status=CourseStatus.published,
            instructor_id=None,
            user=admin
        )
        
        assert course.title == "Admin Course"

    def test_student_cannot_create_course(self, db, student_user):
        """Students cannot create courses."""
        from fastapi import HTTPException
        service = CourseService(db)
        
        with pytest.raises(HTTPException) as exc:
            service.create_course(
                title="Student Course",
                description="Should fail",
                course_status=CourseStatus.draft,
                instructor_id=None,
                user=student_user
            )
        
        assert exc.value.status_code == 403
        assert "instructor" in str(exc.value.detail).lower()

    def test_instructor_cannot_set_other_instructor(self, db, instructor_user):
        """Instructor cannot assign course to another instructor."""
        from fastapi import HTTPException
        service = CourseService(db)
        other_instructor_id = uuid4()
        
        with pytest.raises(HTTPException) as exc:
            service.create_course(
                title="Course",
                description="Test",
                course_status=CourseStatus.draft,
                instructor_id=other_instructor_id,
                user=instructor_user
            )
        
        assert exc.value.status_code == 403

    def test_admin_can_set_any_instructor(self, db, admin_role, instructor_user):
        """Admin can assign course to any instructor."""
        admin = User(
            id=uuid4(),
            email="admin2@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Admin User"
        )
        db.add(admin)
        db.flush()
        
        user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()
        db.refresh(admin)
        
        service = CourseService(db)
        
        course = service.create_course(
            title="Course",
            description="Test",
            course_status=CourseStatus.draft,
            instructor_id=instructor_user.id,
            user=admin
        )
        
        assert course.instructor_id == instructor_user.id


class TestCourseRetrieval:
    """Test course retrieval logic."""

    def test_get_published_course_public(self, db, basic_course):
        """Published courses can be retrieved publicly."""
        service = CourseService(db)
        basic_course.status = CourseStatus.published
        db.commit()
        
        course = service.get_course(basic_course.id, public=True)
        
        assert course.id == basic_course.id

    def test_get_draft_course_fails_public(self, db, basic_course):
        """Draft courses cannot be retrieved publicly."""
        service = CourseService(db)
        basic_course.status = CourseStatus.draft
        db.commit()
        
        with pytest.raises(Exception) as exc:
            service.get_course(basic_course.id, public=True)
        
        assert exc.value.status_code == 404

    def test_get_draft_course_succeeds_non_public(self, db, basic_course):
        """Draft courses can be retrieved with public=False."""
        service = CourseService(db)
        basic_course.status = CourseStatus.draft
        db.commit()
        
        course = service.get_course(basic_course.id, public=False)
        
        assert course.id == basic_course.id

    def test_get_nonexistent_course(self, db):
        """Getting non-existent course raises 404."""
        service = CourseService(db)
        fake_id = uuid4()
        
        with pytest.raises(Exception) as exc:
            service.get_course(fake_id)
        
        assert exc.value.status_code == 404

    def test_list_courses_returns_published_only(self, db, instructor_user):
        """list_courses() returns only published courses by default."""
        service = CourseService(db)
        
        # Create published course
        published = Course(
            id=uuid4(),
            title="Published Course",
            description="Test",
            status=CourseStatus.published,
            instructor_id=instructor_user.id
        )
        db.add(published)
        
        # Create draft course
        draft = Course(
            id=uuid4(),
            title="Draft Course",
            description="Test",
            status=CourseStatus.draft,
            instructor_id=instructor_user.id
        )
        db.add(draft)
        db.commit()
        
        courses = service.list_courses()
        
        assert len(courses) == 1
        assert courses[0].status == CourseStatus.published

    def test_list_courses_with_status_filter(self, db, instructor_user):
        """list_courses() can filter by status."""
        service = CourseService(db)
        
        # Create courses with different statuses
        draft = Course(
            id=uuid4(),
            title="Draft",
            status=CourseStatus.draft,
            instructor_id=instructor_user.id
        )
        published = Course(
            id=uuid4(),
            title="Published",
            status=CourseStatus.published,
            instructor_id=instructor_user.id
        )
        db.add_all([draft, published])
        db.commit()
        
        draft_courses = service.list_courses(status_filter=CourseStatus.draft)
        
        assert len(draft_courses) == 1
        assert draft_courses[0].status == CourseStatus.draft


class TestCourseUpdate:
    """Test course update logic."""

    def test_instructor_can_update_own_course(self, db, instructor_user, basic_course):
        """Instructor can update their own course."""
        service = CourseService(db)
        basic_course.instructor_id = instructor_user.id
        db.commit()
        
        updated = service.update_course(
            basic_course.id,
            instructor_user,
            title="Updated Title"
        )
        
        assert updated.title == "Updated Title"

    def test_instructor_cannot_update_others_course(self, db, instructor_user, basic_course, instructor_role):
        """Instructor cannot update another instructor's course."""
        # Create another instructor
        other_instructor = User(
            id=uuid4(),
            email="other@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Other Instructor"
        )
        db.add(other_instructor)
        db.flush()
        
        user_role = UserRole(user_id=other_instructor.id, role_id=instructor_role.id)
        db.add(user_role)
        db.commit()
        
        basic_course.instructor_id = other_instructor.id
        db.commit()
        
        service = CourseService(db)
        
        with pytest.raises(Exception) as exc:
            service.update_course(
                basic_course.id,
                instructor_user,
                title="Hacked Title"
            )
        
        assert exc.value.status_code == 403

    def test_admin_can_update_any_course(self, db, basic_course, admin_role):
        """Admin can update any course."""
        admin = User(
            id=uuid4(),
            email="admin3@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Admin User"
        )
        db.add(admin)
        db.flush()
        
        user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()
        db.refresh(admin)
        
        service = CourseService(db)
        
        updated = service.update_course(
            basic_course.id,
            admin,
            title="Admin Updated"
        )
        
        assert updated.title == "Admin Updated"


class TestCourseDelete:
    """Test course deletion logic."""

    def test_instructor_can_delete_own_course(self, db, instructor_user, basic_course):
        """Instructor can delete their own course."""
        service = CourseService(db)
        basic_course.instructor_id = instructor_user.id
        db.commit()
        
        service.delete_course(basic_course.id, instructor_user)
        
        # Verify deleted
        with pytest.raises(Exception) as exc:
            service.get_course(basic_course.id, public=False)
        assert exc.value.status_code == 404

    def test_instructor_cannot_delete_others_course(self, db, instructor_user, basic_course, instructor_role):
        """Instructor cannot delete another instructor's course."""
        other_instructor = User(
            id=uuid4(),
            email="other2@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Other Instructor"
        )
        db.add(other_instructor)
        db.flush()
        
        user_role = UserRole(user_id=other_instructor.id, role_id=instructor_role.id)
        db.add(user_role)
        db.commit()
        
        basic_course.instructor_id = other_instructor.id
        db.commit()
        
        service = CourseService(db)
        
        with pytest.raises(Exception) as exc:
            service.delete_course(basic_course.id, instructor_user)
        
        assert exc.value.status_code == 403

    def test_admin_can_delete_any_course(self, db, basic_course, admin_role):
        """Admin can delete any course."""
        admin = User(
            id=uuid4(),
            email="admin4@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Admin User"
        )
        db.add(admin)
        db.flush()
        
        user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()
        db.refresh(admin)
        
        service = CourseService(db)
        
        service.delete_course(basic_course.id, admin)
        
        # Verify deleted
        with pytest.raises(Exception):
            service.get_course(basic_course.id, public=False)


class TestCoursePublish:
    """Test course publishing logic."""

    def test_publish_course_with_modules(self, db, instructor_user, basic_course):
        """Course with modules can be published."""
        service = CourseService(db)
        basic_course.instructor_id = instructor_user.id
        basic_course.status = CourseStatus.draft
        db.commit()
        
        # Add a module
        module = Module(
            id=uuid4(),
            course_id=basic_course.id,
            title="Module 1",
            order_index=1
        )
        db.add(module)
        db.commit()
        db.refresh(basic_course)
        
        published = service.publish_course(basic_course.id, instructor_user)
        
        assert published.status == CourseStatus.published

    def test_publish_course_without_modules_fails(self, db, instructor_user, basic_course):
        """Course without modules cannot be published."""
        service = CourseService(db)
        basic_course.instructor_id = instructor_user.id
        basic_course.status = CourseStatus.draft
        db.commit()
        
        with pytest.raises(Exception) as exc:
            service.publish_course(basic_course.id, instructor_user)
        
        assert exc.value.status_code == 400
        assert "module" in str(exc.value.detail).lower()

    def test_publish_already_published_is_idempotent(self, db, instructor_user, basic_course):
        """Publishing already published course is idempotent."""
        service = CourseService(db)
        basic_course.instructor_id = instructor_user.id
        basic_course.status = CourseStatus.published
        db.commit()
        
        # Add a module first
        module = Module(
            id=uuid4(),
            course_id=basic_course.id,
            title="Module 1",
            order_index=1
        )
        db.add(module)
        db.commit()
        db.refresh(basic_course)
        
        result = service.publish_course(basic_course.id, instructor_user)
        
        assert result.status == CourseStatus.published

    def test_non_owner_cannot_publish(self, db, instructor_user, basic_course, instructor_role):
        """Non-owner instructor cannot publish course."""
        other_instructor = User(
            id=uuid4(),
            email="other3@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Other Instructor"
        )
        db.add(other_instructor)
        db.flush()
        
        user_role = UserRole(user_id=other_instructor.id, role_id=instructor_role.id)
        db.add(user_role)
        db.commit()
        
        basic_course.instructor_id = other_instructor.id
        db.commit()
        
        service = CourseService(db)
        
        with pytest.raises(Exception) as exc:
            service.publish_course(basic_course.id, instructor_user)
        
        assert exc.value.status_code == 403


class TestPrerequisiteLogic:
    """Test prerequisite business logic in service layer."""

    def test_add_prerequisite_success(self, db, instructor_user, basic_course, advanced_course):
        """Adding valid prerequisite succeeds."""
        service = CourseService(db)
        advanced_course.instructor_id = instructor_user.id
        db.commit()
        
        result = service.add_prerequisite(
            advanced_course.id,
            basic_course.id,
            instructor_user
        )
        
        assert basic_course in result.prerequisites

    def test_add_prerequisite_is_idempotent(self, db, instructor_user, basic_course, advanced_course):
        """Adding same prerequisite twice is idempotent."""
        service = CourseService(db)
        advanced_course.instructor_id = instructor_user.id
        db.commit()
        
        service.add_prerequisite(advanced_course.id, basic_course.id, instructor_user)
        result = service.add_prerequisite(advanced_course.id, basic_course.id, instructor_user)
        
        # Should only appear once
        prereq_ids = [c.id for c in result.prerequisites]
        assert prereq_ids.count(basic_course.id) == 1

    def test_cannot_add_self_as_prerequisite(self, db, instructor_user, basic_course):
        """Course cannot be its own prerequisite."""
        service = CourseService(db)
        basic_course.instructor_id = instructor_user.id
        db.commit()
        
        with pytest.raises(Exception) as exc:
            service.add_prerequisite(basic_course.id, basic_course.id, instructor_user)
        
        assert exc.value.status_code == 400
        assert "itself" in str(exc.value.detail).lower()

    def test_add_nonexistent_prerequisite_fails(self, db, instructor_user, basic_course):
        """Adding non-existent course as prerequisite fails."""
        service = CourseService(db)
        basic_course.instructor_id = instructor_user.id
        db.commit()
        
        fake_id = uuid4()
        
        with pytest.raises(Exception) as exc:
            service.add_prerequisite(basic_course.id, fake_id, instructor_user)
        
        assert exc.value.status_code == 404

    def test_non_owner_cannot_add_prerequisite(self, db, instructor_user, basic_course, advanced_course, instructor_role):
        """Non-owner cannot add prerequisites."""
        other_instructor = User(
            id=uuid4(),
            email="other4@test.com",
            password_hash=get_password_hash("password123"),
            full_name="Other Instructor"
        )
        db.add(other_instructor)
        db.flush()
        
        user_role = UserRole(user_id=other_instructor.id, role_id=instructor_role.id)
        db.add(user_role)
        db.commit()
        
        advanced_course.instructor_id = other_instructor.id
        db.commit()
        
        service = CourseService(db)
        
        with pytest.raises(Exception) as exc:
            service.add_prerequisite(advanced_course.id, basic_course.id, instructor_user)
        
        assert exc.value.status_code == 403

    def test_remove_prerequisite_success(self, db, instructor_user):
        """Removing existing prerequisite succeeds."""
        from app.modules.courses.models import Course
        service = CourseService(db)
        
        # Create fresh courses for this test
        course1 = Course(
            id=uuid4(),
            title="Course 1",
            status=CourseStatus.draft,
            instructor_id=instructor_user.id
        )
        course2 = Course(
            id=uuid4(),
            title="Course 2",
            status=CourseStatus.draft,
            instructor_id=instructor_user.id
        )
        db.add_all([course1, course2])
        db.commit()
        
        # Add prerequisite using service
        service.add_prerequisite(course2.id, course1.id, instructor_user)
        db.refresh(course2)
        assert course1 in course2.prerequisites
        
        # Remove prerequisite
        service.remove_prerequisite(course2.id, course1.id, instructor_user)
        
        db.refresh(course2)
        assert course1 not in course2.prerequisites

    def test_remove_prerequisite_is_idempotent(self, db, instructor_user, basic_course, advanced_course):
        """Removing non-existent prerequisite is idempotent."""
        service = CourseService(db)
        advanced_course.instructor_id = instructor_user.id
        db.commit()
        
        # Should not raise error even if not present
        service.remove_prerequisite(advanced_course.id, basic_course.id, instructor_user)

    def test_list_prerequisites(self, db, instructor_user):
        """Listing prerequisites returns correct courses."""
        from app.modules.courses.models import Course
        service = CourseService(db)
        
        # Create fresh courses for this test
        course1 = Course(
            id=uuid4(),
            title="Prerequisite Course",
            status=CourseStatus.published,
            instructor_id=instructor_user.id
        )
        course2 = Course(
            id=uuid4(),
            title="Main Course",
            status=CourseStatus.published,
            instructor_id=instructor_user.id
        )
        db.add_all([course1, course2])
        db.commit()
        
        # Add prerequisite using service
        service.add_prerequisite(course2.id, course1.id, instructor_user)
        
        prerequisites = service.list_prerequisites(course2.id)
        
        assert len(prerequisites) == 1
        assert prerequisites[0].id == course1.id
