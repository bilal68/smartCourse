# SmartCourse LMS - Architecture Diagram

## 📁 New File Structure

```
smartcourse/
├── .venv/
├── alembic/                    # Database migrations
│   └── versions/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── celery_app.py           # Celery configuration
│   │
│   ├── core/                   # Core utilities
│   │   ├── config.py           # Settings & configuration
│   │   ├── env.py              # Environment loading
│   │   ├── logging.py          # Structured logging
│   │   └── security.py         # JWT, password hashing
│   │
│   ├── db/                     # Database layer
│   │   ├── base.py             # SQLAlchemy Base + model imports
│   │   ├── deps.py             # FastAPI dependencies (get_db, get_current_user)
│   │   ├── mixins.py           # TimestampMixin, etc.
│   │   └── session.py          # Database session factory
│   │
│   ├── middleware/             # 🆕 Request/response middleware
│   │   ├── auth.py             # JWT auth middleware (optional)
│   │   └── logging.py          # Request logging with timing
│   │
│   ├── integrations/           # 🆕 External services
│   │   └── kafka/
│   │       ├── producer.py     # Kafka message publisher
│   │       └── consumer_worker.py  # Kafka message consumer
│   │
│   ├── modules/                # 🆕 Domain modules (bounded contexts)
│   │   │
│   │   ├── auth/               # Authentication & Authorization
│   │   │   ├── models.py       # User, Role, UserRole
│   │   │   ├── repository.py   # UserRepository, RoleRepository
│   │   │   ├── service.py      # AuthService (register, login)
│   │   │   └── routes.py       # /auth/register, /auth/login
│   │   │
│   │   ├── courses/            # Course Management
│   │   │   ├── models.py       # Course, Module, LearningAsset
│   │   │   ├── repository.py   # CourseRepository, ModuleRepository, AssetRepository
│   │   │   ├── service.py      # CourseService (CRUD + publish)
│   │   │   └── routes.py       # /courses/* endpoints
│   │   │
│   │   ├── enrollments/        # Student Enrollments
│   │   │   ├── models.py       # Enrollment
│   │   │   ├── repository.py   # EnrollmentRepository
│   │   │   ├── service.py      # EnrollmentService
│   │   │   └── routes.py       # /enrollments/* endpoints
│   │   │
│   │   └── progress/           # Progress Tracking
│   │       ├── models.py       # CourseProgress, AssetProgress
│   │       ├── repository.py   # ProgressRepository
│   │       ├── service.py      # ProgressService
│   │       └── routes.py       # /progress/* endpoints
│   │
│   ├── tasks/                  # Celery async tasks
│   │   ├── certificate_tasks.py
│   │   ├── enrollment_tasks.py
│   │   ├── notification_tasks.py
│   │   ├── outbox_tasks.py     # Publishes pending outbox events
│   │   └── progress_task.py
│   │
│   ├── schemas/                # Pydantic schemas (shared)
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── course.py
│   │   ├── module.py
│   │   ├── asset.py
│   │   ├── enrollment.py
│   │   └── progress.py
│   │
│   ├── models/                 # Shared models (not in modules)
│   │   ├── outbox_event.py     # Outbox pattern
│   │   ├── certificate.py
│   │   └── content_chunk.py
│   │
│   └── api/                    # API routing
│       └── v1/
│           └── routes/
│               ├── __init__.py # Router registration
│               ├── modules.py  # /modules/* endpoints (legacy)
│               ├── assets.py   # /assets/* endpoints (legacy)
│               └── celery_test.py
│
├── scripts/
│   └── seed.py                 # Database seeding
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── ARCHITECTURE.md             # 🆕 Architecture documentation
└── MIGRATION_SUMMARY.md        # 🆕 Migration guide
```

## 🏗️ Module Architecture

### Each Module Contains:

```
app/modules/{domain}/
├── __init__.py
├── models.py        # SQLAlchemy ORM models
├── repository.py    # Data access layer (CRUD)
├── service.py       # Business logic + authorization
└── routes.py        # FastAPI endpoints
```

### Layer Flow:

```
HTTP Request
     ↓
┌─────────────────────┐
│   FastAPI Routes    │ ← Validates request, calls service
│    (routes.py)      │
└─────────┬───────────┘
          ↓
┌─────────────────────┐
│   Service Layer     │ ← Business logic, authorization
│   (service.py)      │   Transaction management
└─────────┬───────────┘   Domain events (outbox)
          ↓
┌─────────────────────┐
│  Repository Layer   │ ← Data access (CRUD operations)
│  (repository.py)    │   No business logic
└─────────┬───────────┘
          ↓
┌─────────────────────┐
│      Models         │ ← SQLAlchemy ORM models
│    (models.py)      │   Database schema
└─────────────────────┘
```

## 🔐 Authentication Flow

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ POST /api/v1/auth/register
     ↓
┌─────────────────────────────┐
│  AuthService.register_user  │
│  • Validate email unique    │
│  • Hash password            │
│  • Create user in DB        │
└─────────────┬───────────────┘
              │
              ↓
┌─────────────────────────────┐
│    UserRepository.create    │
│    • Insert into DB         │
└─────────────┬───────────────┘
              │
              ↓ Commit
┌─────────────────────────────┐
│     Return User + 201       │
└─────────────────────────────┘

┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ POST /api/v1/auth/login
     ↓
┌─────────────────────────────┐
│    AuthService.login        │
│  • Find user by email       │
│  • Verify password          │
│  • Create JWT token         │
└─────────────┬───────────────┘
              │
              ↓
┌─────────────────────────────┐
│   Return JWT Token          │
└─────────────────────────────┘
```

## 🎓 Course Publishing Flow (Event-Driven)

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ POST /api/v1/courses/{id}/publish
     ↓
┌───────────────────────────────────────┐
│   CourseService.publish_course        │
│   • Check authorization (instructor)  │
│   • Validate course has modules       │
│   • Change status to 'published'      │
│   • Create OutboxEvent (transactional)│
└───────────────────┬───────────────────┘
                    │
                    ↓ DB Commit (atomic)
┌───────────────────────────────────────┐
│          Database                     │
│   • courses.status = 'published'      │
│   • outbox_events.status = 'pending'  │
└───────────────────┬───────────────────┘
                    │
                    │ (Background)
                    ↓
┌───────────────────────────────────────┐
│  Celery Task: publish_pending_outbox  │
│  • Query pending outbox events        │
│  • Publish each to Kafka              │
│  • Mark as 'published'                │
└───────────────────┬───────────────────┘
                    │
                    ↓
┌───────────────────────────────────────┐
│          Kafka Topic                  │
│   smartcourse.course-events           │
└───────────────────┬───────────────────┘
                    │
                    ↓ (Consumer)
┌───────────────────────────────────────┐
│     Kafka Consumer Worker             │
│   • Receive event                     │
│   • Dispatch to Celery task           │
└───────────────────┬───────────────────┘
                    │
                    ↓
┌───────────────────────────────────────┐
│  Celery Task: notify_course_published │
│   • Send email to subscribers         │
│   • Create notifications              │
└───────────────────────────────────────┘
```

## 📊 Database Schema (Module Boundaries)

```
┌─────────────────────────────────────────────────────────┐
│                    AUTH MODULE                          │
│  ┌───────────┐  ┌───────────┐  ┌──────────────┐       │
│  │   users   │  │   roles   │  │  user_roles  │       │
│  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘       │
│        │              │                 │               │
└────────┼──────────────┼─────────────────┼───────────────┘
         │              │                 │
┌────────▼──────────────▼─────────────────▼───────────────┐
│                  COURSES MODULE                          │
│  ┌─────────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │   courses   │  │ modules  │  │ learning_assets  │   │
│  │ (instructor)│  │          │  │                  │   │
│  └─────┬───────┘  └────┬─────┘  └────┬─────────────┘   │
│        │               │              │                 │
└────────┼───────────────┼──────────────┼─────────────────┘
         │               │              │
┌────────▼───────────────▼──────────────▼─────────────────┐
│               ENROLLMENTS MODULE                         │
│  ┌─────────────────┐                                    │
│  │   enrollments   │                                    │
│  │  (user+course)  │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
└───────────┼─────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────┐
│                PROGRESS MODULE                           │
│  ┌──────────────────┐  ┌────────────────────┐          │
│  │ course_progress  │  │  asset_progress    │          │
│  │  (enrollment)    │  │  (enrollment+asset)│          │
│  └──────────────────┘  └────────────────────┘          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              SHARED MODELS (not in modules)              │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  outbox_events   │  │  certificates    │            │
│  └──────────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Deployment Architecture (Future Microservices)

```
                    ┌─────────────────┐
                    │   API Gateway   │
                    │   (Kong/Traefik)│
                    └────────┬────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
        ┌───────▼──────┐ ┌──▼────────┐ ┌▼────────────┐
        │ LMS Service  │ │AI Service │ │Analytics    │
        │ (FastAPI)    │ │(FastAPI)  │ │Service      │
        └───────┬──────┘ └──┬────────┘ └┬────────────┘
                │           │            │
        ┌───────▼──────┐ ┌──▼────────┐ ┌▼────────────┐
        │  Postgres    │ │ Postgres  │ │  Postgres   │
        └──────────────┘ └───────────┘ └─────────────┘
                │           │            │
                └───────────┼────────────┘
                            │
                    ┌───────▼────────┐
                    │     Kafka      │
                    │   (Event Bus)  │
                    └────────────────┘
```

## 📈 Scalability Path

### Current: Modular Monolith ✅
- All modules in one service
- Single database
- Clean boundaries for future split

### Phase 1: Separate Database per Module
- `lms_auth_db`, `lms_courses_db`, etc.
- Still one service, but DB isolation

### Phase 2: Extract Services
- Split modules into separate services
- Each with its own database
- Communicate via Kafka events

### Phase 3: Shared Library
```python
# smartcourse-common (published package)
from smartcourse_common.auth import validate_jwt
from smartcourse_common.events import CoursePublishedEvent
```

## 🎯 Key Benefits

✅ **Clean Architecture** - Separation of concerns
✅ **Testability** - Easy to mock dependencies
✅ **Maintainability** - Self-contained modules
✅ **Scalability** - Can split into microservices
✅ **Reliability** - Outbox pattern for events
✅ **Security** - RBAC in service layer
✅ **Performance** - Repository pattern reduces queries

## 📚 Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture
- [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) - Migration guide
- Module examples in `app/modules/*/`

Your LMS is now production-ready! 🎉
