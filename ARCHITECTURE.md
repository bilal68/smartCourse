# SmartCourse LMS - Modular Architecture

## Project Structure

The application has been refactored into a modular architecture for better organization and scalability.

```
app/
├── core/                   # Core utilities (config, logging, security)
├── db/                     # Database configuration and dependencies
├── middleware/             # Request/response middleware (auth, logging)
├── integrations/           # External service integrations
│   └── kafka/             # Kafka producer & consumer
├── modules/                # Domain modules (bounded contexts)
│   ├── auth/              # Authentication & Authorization
│   │   ├── models.py      # User, Role, UserRole models
│   │   ├── repository.py  # Data access layer
│   │   ├── service.py     # Business logic
│   │   └── routes.py      # API endpoints
│   ├── courses/           # Course Management
│   │   ├── models.py      # Course, Module, LearningAsset models
│   │   ├── repository.py  # Data access layer
│   │   ├── service.py     # Business logic
│   │   └── routes.py      # API endpoints
│   ├── enrollments/       # Student Enrollments
│   │   ├── models.py      # Enrollment model
│   │   ├── repository.py  # Data access layer
│   │   ├── service.py     # Business logic
│   │   └── routes.py      # API endpoints
│   └── progress/          # Progress Tracking
│       ├── models.py      # CourseProgress, AssetProgress models
│       ├── repository.py  # Data access layer
│       ├── service.py     # Business logic
│       └── routes.py      # API endpoints
├── tasks/                  # Celery async tasks
├── schemas/                # Pydantic schemas (shared)
├── models/                 # Shared models (outbox_event, certificate)
└── api/
    └── v1/
        └── routes/        # Legacy routes (being migrated)

```

## Module Architecture

Each module follows a layered architecture:

### 1. **Models Layer** (`models.py`)
- SQLAlchemy ORM models
- Database schema definitions
- Relationships between entities

### 2. **Repository Layer** (`repository.py`)
- Data access abstraction
- CRUD operations
- Query methods
- No business logic

### 3. **Service Layer** (`service.py`)
- Business logic
- Authorization checks
- Transaction management
- Orchestrates repositories
- Emits domain events (via outbox pattern)

### 4. **Routes Layer** (`routes.py`)
- FastAPI endpoints
- Request/response handling
- Delegates to service layer
- Minimal logic

## Key Design Patterns

### Repository Pattern
```python
# Separates data access from business logic
class CourseRepository:
    def get_by_id(self, course_id: UUID) -> Optional[Course]:
        return self.db.query(Course).filter(Course.id == course_id).first()
```

### Service Layer Pattern
```python
# Encapsulates business logic and orchestration
class CourseService:
    def create_course(self, title: str, user: User) -> Course:
        # Authorization
        self._check_permission(user)
        
        # Business logic
        course = self.course_repo.create(title=title)
        
        # Commit transaction
        self.db.commit()
        return course
```

### Outbox Pattern
```python
# Emit events reliably for async processing
outbox = OutboxEvent(
    event_type="course.published",
    aggregate_id=course.id,
    payload={...},
    status=OutboxStatus.pending,
)
db.add(outbox)
db.commit()
```

## Module Dependencies

```
┌─────────────────────────────────────────┐
│              API Routes                 │
│         (FastAPI endpoints)             │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│           Service Layer                 │
│      (Business logic + Auth)            │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Repository Layer                │
│         (Data access)                   │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│             Models                      │
│       (SQLAlchemy ORM)                  │
└─────────────────────────────────────────┘
```

## Authentication & Authorization

### JWT Authentication (in LMS service)
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Get JWT token

### RBAC (Role-Based Access Control)
```python
# Roles: student, instructor, admin
user.roles  # List of Role objects

# Service layer checks permissions
def create_course(self, user: User):
    role_names = [r.name for r in user.roles]
    if "instructor" not in role_names:
        raise HTTPException(status_code=403, detail="Forbidden")
```

## Event-Driven Architecture

### Outbox Pattern with Kafka

1. **Emit Event** (transactional)
```python
# In service layer
course.status = CourseStatus.published

outbox = OutboxEvent(
    event_type="course.published",
    aggregate_id=course.id,
    payload={"course_id": str(course.id), ...},
    status=OutboxStatus.pending,
)
db.add(outbox)
db.commit()  # Atomic with domain changes
```

2. **Publish to Kafka** (async via Celery)
```python
# Celery task polls outbox table
@celery_app.task
def publish_pending_outbox():
    events = db.query(OutboxEvent).filter(status=pending).all()
    for evt in events:
        publish_json(topic=TOPIC_MAP[evt.event_type], value=evt.payload)
        evt.status = OutboxStatus.published
    db.commit()
```

3. **Consume Events** (other services)
```python
# Consumer worker in each service
from app.integrations.kafka import start_consumer

# Routes to Celery tasks
celery_app.send_task("notify_course_published", args=[payload])
```

## Integration Points

### Kafka Integration
- **Location**: `app/integrations/kafka/`
- **Producer**: Publishes events to topics
- **Consumer**: Consumes events and dispatches to Celery tasks

### Middleware
- **Auth Middleware**: JWT validation (optional global)
- **Logging Middleware**: Request/response logging with timing

## Database Migrations

All models are imported in `app/db/base.py` for Alembic:

```python
from app.modules.auth.models import User, Role, UserRole
from app.modules.courses.models import Course, Module, LearningAsset
from app.modules.enrollments.models import Enrollment
from app.modules.progress.models import CourseProgress, AssetProgress
```

## Running the Application

### Development
```bash
# Start FastAPI
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Start Celery worker
.\.venv\Scripts\python.exe -m celery -A app.celery_app:celery_app worker --loglevel=DEBUG --pool=solo

# Start Celery beat (periodic tasks)
.\.venv\Scripts\python.exe -m celery -A app.celery_app:celery_app beat --loglevel=info
```

### Or use VS Code tasks (dev:all)
- Runs FastAPI, Celery worker, and Celery beat in parallel

## Future Enhancements

1. **Microservices Split** (when needed)
   - Split modules into separate services
   - Each service has its own DB
   - Communicate via Kafka events

2. **Shared Library**
   - Extract common code (JWT validation, models)
   - Publish as internal package
   - Each service imports shared lib

3. **Observability Module**
   - OpenTelemetry tracing
   - Prometheus metrics
   - Structured logging aggregation

4. **API Gateway**
   - Kong or similar
   - Centralized auth
   - Rate limiting
   - Request routing

## Migration Notes

### What Changed
- ✅ Models moved to `app/modules/{domain}/models.py`
- ✅ Routes moved to `app/modules/{domain}/routes.py`
- ✅ Added Repository pattern for data access
- ✅ Added Service layer for business logic
- ✅ Middleware folder for cross-cutting concerns
- ✅ Integrations folder for external services (Kafka)
- ✅ All imports updated throughout codebase

### Backward Compatibility
- Old route imports still work (re-exported)
- Database schema unchanged
- API endpoints unchanged

## Best Practices

1. **Always use Service layer** - Don't query models directly in routes
2. **Keep repositories thin** - Only data access, no business logic
3. **Authorization in services** - Check permissions before actions
4. **Use outbox pattern** - Never publish to Kafka directly in routes
5. **Transaction boundaries** - Commit in service layer, not repositories
6. **Type hints everywhere** - Better IDE support and type safety

## Questions?

See example implementations in:
- `app/modules/auth/` - Simple CRUD with auth
- `app/modules/courses/` - Complex domain with authorization
- `app/modules/enrollments/` - Many-to-many relationships
- `app/modules/progress/` - Calculated aggregates
