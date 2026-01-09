# LMS Service

Core Learning Management System service handling user management, courses, enrollments, and progress tracking.

## Features

- 👤 **User Authentication & Authorization** (JWT + RBAC)
- 📚 **Course Management** (CRUD operations, publishing)
- 📝 **Module & Asset Management** (course content structure)
- 🎓 **Enrollment Management** (student enrollments)
- 📊 **Progress Tracking** (course and asset completion)
- 📨 **Event Publishing** (Kafka outbox pattern)

## Architecture

```
app/
├── main.py              # FastAPI application
├── celery_app.py        # Celery configuration
├── modules/             # Domain modules
│   ├── auth/           # Authentication & authorization
│   ├── courses/        # Course management
│   ├── enrollments/    # Student enrollments
│   └── progress/       # Progress tracking
├── core/               # Core utilities
├── db/                 # Database layer
├── tasks/              # Celery tasks
└── integrations/       # External services (Kafka)
```

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed database
python scripts/seed.py

# Start API
uvicorn app.main:app --reload

# Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Start Celery beat
celery -A app.celery_app beat --loglevel=info
```

## API Endpoints

- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/courses` - List courses
- `POST /api/v1/courses` - Create course
- `POST /api/v1/courses/{id}/publish` - Publish course
- `POST /api/v1/enrollments` - Create enrollment
- `POST /api/v1/progress/assets/{id}` - Update asset progress

## Events Published

- `user.registered` - When user registers
- `user.role_assigned` - When role assigned to user
- `course.created` - When course is created
- `course.published` - When course is published
- `enrollment.created` - When enrollment is created
- `enrollment.completed` - When enrollment is completed

## Database Schema

- **users** - User accounts
- **roles** - Role definitions (student, instructor, admin)
- **user_roles** - User-role assignments
- **courses** - Course catalog
- **modules** - Course modules
- **learning_assets** - Learning content (video, quiz, etc.)
- **enrollments** - Student enrollments
- **course_progress** - Course completion tracking
- **asset_progress** - Asset completion tracking
- **outbox_events** - Event outbox for reliable messaging
