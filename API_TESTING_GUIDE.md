# SmartCourse API Testing Guide

## Overview
This document provides a step-by-step guide for testing the SmartCourse microservices using the provided Postman collection.

## Prerequisites
1. **Import Collections**: Import both JSON files into Postman:
   - `SmartCourse API Collection.postman_collection.json`
   - `SmartCourse Development Environment.postman_environment.json`

2. **Select Environment**: In Postman, select "SmartCourse Development Environment" from the environment dropdown.

3. **Start Services**: Ensure all services are running:
   - LMS FastAPI Service (port 8000)
   - AI FastAPI Service (port 8001)
   - PostgreSQL Database
   - Kafka Server
   - Celery Worker
   - Celery Beat (optional for scheduled tasks)

## Testing Workflow

### 1. Authentication Setup
#### Register an Instructor
```
POST {{lms_base_url}}/api/v1/auth/register
```
- Uses predefined instructor credentials from environment
- Creates a user with instructor privileges

#### Login to Get Access Token
```
POST {{lms_base_url}}/api/v1/auth/login
```
- Automatically stores the `access_token` in environment variables
- Required for all subsequent authenticated requests

### 2. Course Management

#### Create a Course
```
POST {{lms_base_url}}/api/v1/courses
```
- Automatically stores `course_id` in environment for subsequent requests
- Creates course with status: "draft"

#### View All Courses
```
GET {{lms_base_url}}/api/v1/courses
```
- Lists all courses accessible to the authenticated user

#### Get Specific Course
```
GET {{lms_base_url}}/api/v1/courses/{{course_id}}
```
- Uses stored course_id from create request

### 3. Module Management

#### Create Course Module
```
POST {{lms_base_url}}/api/v1/modules
```
- Automatically stores `module_id` in environment
- Links to the previously created course

#### List Modules by Course
```
GET {{lms_base_url}}/api/v1/modules/by-course/{{course_id}}
```
- Shows all modules for the specific course

### 4. Learning Assets

#### Create Learning Asset
```
POST {{lms_base_url}}/api/v1/assets
```
- Automatically stores `asset_id` in environment
- Links to the previously created module
- Includes sample content URL for testing content processing

#### List Assets by Module
```
GET {{lms_base_url}}/api/v1/assets/by-module/{{module_id}}
```
- Shows all assets for the specific module

### 5. Course Publishing (Event-Driven Workflow)

#### Publish Course
```
POST {{lms_base_url}}/api/v1/courses/{{course_id}}/publish
```
**This triggers the complete event-driven workflow:**

1. **LMS Service**: Updates course status to "published"
2. **Outbox Event**: Creates `course.published` event with course data
3. **Kafka Producer**: Publishes event to "course.events" topic
4. **AI Service**: Kafka consumer receives the event
5. **Content Processing**: AI service processes course assets
6. **Content Chunking**: Creates content chunks for each asset
7. **Response Event**: AI publishes `content.processed` event back
8. **LMS Consumer**: Receives and processes the response
9. **Status Update**: Updates course processing status to "ready"

#### Monitor Processing Status
After publishing, check the course again to see processing status:
```
GET {{lms_base_url}}/api/v1/courses/{{course_id}}
```
Look for the `processing_status` field which should progress from:
- `not_started` → `processing` → `ready`

### 6. Student Enrollment & Progress

#### Create Student Account
First, register a student user by changing the environment variables:
- Set `student_email`, `student_name`, `student_password`
- Use the register endpoint with student credentials
- Store the returned user ID in `student_user_id`

#### Create Enrollment
```
POST {{lms_base_url}}/api/v1/enrollments
```
- Automatically stores `enrollment_id` in environment
- Links student to the published course

#### Track Asset Progress
```
POST {{lms_base_url}}/api/v1/progress/assets/{{asset_id}}
```
- Update progress percentage and completion status
- Triggers automatic course progress recalculation

#### View Course Progress
```
GET {{lms_base_url}}/api/v1/progress/courses/{{course_id}}/enrollment/{{enrollment_id}}
```
- Shows overall course completion metrics

### 7. AI Service Health Check

#### Check AI Service Status
```
GET {{ai_base_url}}/health
```
- Verifies AI service is running and healthy

#### Get AI Service Info
```
GET {{ai_base_url}}/
```
- Returns AI service metadata and status

### 8. Celery Task Testing

#### Test Async Task
```
POST {{lms_base_url}}/api/v1/celery-test/async-task
```
- Tests Celery worker functionality
- Returns task_id for monitoring

#### Check Task Status
```
GET {{lms_base_url}}/api/v1/celery-test/task-status/{{task_id}}
```
- Monitors async task execution status

## Environment Variables Reference

### Service URLs
- `lms_base_url`: http://localhost:8000
- `ai_base_url`: http://localhost:8001

### Authentication
- `access_token`: Auto-populated after login
- `instructor_email`: instructor@example.com
- `instructor_password`: instructor123
- `student_email`: student@example.com
- `student_password`: student123

### Auto-Generated IDs
These are automatically populated by test scripts:
- `course_id`: UUID of created course
- `module_id`: UUID of created module
- `asset_id`: UUID of created asset
- `enrollment_id`: UUID of created enrollment
- `student_user_id`: UUID of student user
- `task_id`: UUID of async task

### Sample Data
- `course_title`: "Introduction to Machine Learning"
- `course_description`: Comprehensive ML course description
- `module_title`: "Linear Regression Fundamentals"
- `asset_title`: "Linear Regression Theory"
- `asset_type`: "document"
- `asset_source_url`: Sample content URL

## Testing Complete Event-Driven Workflow

### End-to-End Test Sequence:
1. **Register & Login** → Get access token
2. **Create Course** → Store course_id
3. **Create Module** → Store module_id
4. **Create Asset** → Store asset_id (with content URL)
5. **Publish Course** → Triggers event-driven processing
6. **Monitor Kafka Logs** → Watch event flow between services
7. **Check Processing Status** → Verify course.processing_status updates
8. **Create Student & Enrollment** → Setup for progress tracking
9. **Track Progress** → Test learning analytics

### Monitoring Points:
- **LMS Logs**: Course publishing and status updates
- **Kafka Logs**: Event publishing and consumption
- **AI Service Logs**: Content processing operations
- **Celery Logs**: Background task execution
- **Database**: Check outbox_events, content_chunks tables

## Troubleshooting

### Common Issues:
1. **401 Unauthorized**: Ensure access_token is set after login
2. **404 Not Found**: Check that resource IDs are correctly stored
3. **403 Forbidden**: Verify user has appropriate role permissions
4. **Service Unavailable**: Ensure all microservices are running

### Debug Steps:
1. Check environment variable values in Postman
2. Verify all services are responding to health checks
3. Monitor service logs for errors
4. Check database for expected data changes
5. Verify Kafka topic messages are flowing correctly

## Expected Results

### Successful Course Publishing:
- Course status changes to "published"
- Outbox event created with "pending" status
- Kafka message published to "course.events" topic
- AI service receives and processes the event
- Content chunks created and stored
- Course processing_status updated to "ready"
- Outbox event status updated to "processed"

This collection provides comprehensive testing coverage for the entire SmartCourse microservices architecture with proper variable management and automated ID tracking.