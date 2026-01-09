# 🎓 SmartCourse - Microservices LMS Platform

Modern Learning Management System built with **microservices architecture**, **event-driven communication**, and **Domain-Driven Design (DDD)** principles.

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                     API Gateway (Future)                    │
│              JWT Validation + Header Injection             │
└──────────────┬─────────────────┬───────────────┬───────────┘
               │                 │               │
    ┌──────────▼──────┐  ┌──────▼──────┐  ┌────▼────────┐
    │  LMS Service    │  │ AI Service  │  │ Analytics   │
    │  Port: 8000     │  │ Port: 8001  │  │ Port: 8002  │
    │                 │  │             │  │             │
    │ • Auth          │  │ • Chat      │  │ • Metrics   │
    │ • Courses       │  │ • GenAI     │  │ • Reports   │
    │ • Enrollments   │  │ • Recommend │  │ • Dashboards│
    │ • Progress      │  │             │  │             │
    └────────┬────────┘  └──────┬──────┘  └──────┬──────┘
             │                  │                 │
             │                  ↓                 │
             │          ┌───────────────┐        │
             │          │ Notification  │        │
             │          │   (Worker)    │        │
             │          │ • Email       │        │
             │          │ • SMS         │        │
             │          └───────┬───────┘        │
             │                  │                 │
             └──────────────────┼─────────────────┘
                                │
                        ┌───────▼────────┐
                        │     Kafka      │
                        │  (Event Bus)   │
                        └────────────────┘
```

## 📁 Project Structure

```
smartcourse/
├── services/
│   ├── lms/                    # 🎓 LMS Service (Main)
│   │   ├── app/
│   │   │   ├── modules/        # Domain modules
│   │   │   │   ├── auth/       # Authentication & RBAC
│   │   │   │   ├── courses/    # Course management
│   │   │   │   ├── enrollments/# Enrollment handling
│   │   │   │   └── progress/   # Progress tracking
│   │   │   ├── core/           # Core utilities
│   │   │   ├── db/             # Database layer
│   │   │   ├── tasks/          # Celery tasks
│   │   │   └── integrations/   # Kafka integration
│   │   ├── alembic/            # Database migrations
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   ├── ai/                     # 🤖 AI Service
│   │   ├── app/
│   │   │   └── main.py         # FastAPI app
│   │   ├── Dockerfile
│   │   └── README.md
│   │
│   ├── analytics/              # 📊 Analytics Service
│   │   ├── app/
│   │   │   └── main.py         # FastAPI app
│   │   ├── Dockerfile
│   │   └── README.md
│   │
│   └── notification/           # 📧 Notification Service
│       ├── app/
│       │   ├── celery_app.py   # Celery worker
│       │   └── tasks/          # Email/SMS tasks
│       ├── Dockerfile
│       └── README.md
│
├── infrastructure/
│   └── docker-compose.yml      # Multi-service orchestration
│
├── ARCHITECTURE.md             # Detailed architecture docs
├── MIGRATION_SUMMARY.md        # Modular monolith migration guide
└── README.md                   # This file
```

## 🚀 Services

### 1️⃣ LMS Service (Port 8000)
**Core learning management functionality**

- ✅ **Implemented** - Fully functional
- **Database**: `lms_db` (PostgreSQL)
- **Tech Stack**: FastAPI, SQLAlchemy, Celery, Kafka
- **Features**:
  - User registration & JWT authentication
  - Role-Based Access Control (RBAC)
  - Course CRUD operations
  - Module & asset management
  - Student enrollments
  - Progress tracking
  - Outbox pattern for events

**API Docs**: http://localhost:8000/docs

### 2️⃣ AI Service (Port 8001)
**AI-powered content generation and recommendations**

- 🚧 **Skeleton** - Ready for implementation
- **Database**: None (stateless service)
- **Tech Stack**: FastAPI, OpenAI, LangChain
- **Planned Features**:
  - AI chat assistant
  - Quiz generation
  - Course summaries
  - Personalized recommendations
  - Content embeddings

**API Docs**: http://localhost:8001/docs (when running)

### 3️⃣ Analytics Service (Port 8002)
**Real-time analytics and reporting**

- 🚧 **Skeleton** - Ready for implementation
- **Database**: `analytics_db` (PostgreSQL/TimescaleDB)
- **Tech Stack**: FastAPI, Pandas, SQLAlchemy
- **Planned Features**:
  - Learning analytics
  - Course performance metrics
  - Completion rate tracking
  - Engagement analytics
  - Custom reports

**API Docs**: http://localhost:8002/docs (when running)

### 4️⃣ Notification Service
**Background worker for notifications**

- 🚧 **Skeleton** - Ready for implementation
- **Database**: None (uses LMS DB for user data)
- **Tech Stack**: Celery, SendGrid, Twilio
- **Planned Features**:
  - Email notifications
  - SMS notifications
  - Push notifications
  - Template management

**No HTTP API** - Celery worker only

## 🔧 Technology Stack

| Component | Technology |
|-----------|-----------|
| **API Framework** | FastAPI 0.109+ |
| **Database** | PostgreSQL 16 |
| **ORM** | SQLAlchemy 2.0 |
| **Migrations** | Alembic |
| **Task Queue** | Celery 5.3 + RabbitMQ |
| **Event Bus** | Apache Kafka 7.6 |
| **Schema Registry** | Confluent Schema Registry |
| **Caching** | Redis 7 |
| **Auth** | JWT (python-jose) |
| **Containerization** | Docker + Docker Compose |

## 🏃 Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Git

### 1. Clone Repository

```bash
git clone https://github.com/yourcompany/smartcourse.git
cd smartcourse
```

### 2. Start Infrastructure Services

```bash
cd infrastructure
docker-compose up -d postgres redis rabbitmq kafka schema-registry
```

### 3. Run LMS Service (Development)

```bash
cd services/lms

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed database (optional)
python scripts/seed.py

# Start API
uvicorn app.main:app --reload --port 8000

# Start Celery worker (new terminal)
celery -A app.celery_app worker --loglevel=info --pool=solo

# Start Celery beat (new terminal)
celery -A app.celery_app beat --loglevel=info
```

### 4. Run All Services with Docker

```bash
cd infrastructure
docker-compose up -d
```

**Services will be available at:**
- LMS API: http://localhost:8000
- AI Service: http://localhost:8001
- Analytics Service: http://localhost:8002
- Kafka UI: http://localhost:8080
- RabbitMQ: http://localhost:15672

## 📡 Event-Driven Architecture

Services communicate asynchronously via **Kafka events**:

### Events Published by LMS

| Event | Topic | Consumers |
|-------|-------|-----------|
| `user.registered` | `smartcourse.user-events` | Notification |
| `course.published` | `smartcourse.course-events` | AI, Analytics, Notification |
| `enrollment.created` | `smartcourse.enrollment-events` | AI, Analytics, Notification |
| `enrollment.completed` | `smartcourse.enrollment-events` | Notification |

### Outbox Pattern

LMS service uses **transactional outbox pattern** for reliable event delivery:
1. Business logic + outbox event saved in **same transaction**
2. Celery task polls outbox every 10 seconds
3. Publishes pending events to Kafka
4. Marks events as published

## 🗄️ Database Architecture

Each service has its **own database** (Database-per-Service pattern):

```
┌─────────────────┐  ┌─────────────────┐
│    lms_db       │  │  analytics_db   │
│                 │  │                 │
│ • users         │  │ • user_metrics  │
│ • roles         │  │ • course_metrics│
│ • courses       │  │ • events        │
│ • enrollments   │  │                 │
│ • progress      │  └─────────────────┘
│ • outbox_events │
└─────────────────┘
```

## 🔐 Authentication Flow

1. **User Registration**: `POST /api/v1/auth/register`
2. **Login**: `POST /api/v1/auth/login` → Returns JWT token
3. **Protected Endpoints**: Include `Authorization: Bearer <token>` header
4. **API Gateway** (future): Validates JWT, adds `X-User-Id` header
5. **Services**: Trust gateway, read user from header

## 🛠️ Development Workflow

### Adding New Features

1. **LMS Service**: Work in `services/lms/app/modules/{domain}/`
2. **AI Service**: Work in `services/ai/app/`
3. **Analytics**: Work in `services/analytics/app/`
4. **Notification**: Work in `services/notification/app/tasks/`

### Testing

```bash
# LMS service tests
cd services/lms
pytest

# AI service tests
cd services/ai
pytest
```

### Database Migrations

```bash
cd services/lms

# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head
```

## 📊 Monitoring & Observability

- **Kafka UI**: http://localhost:8080 - Monitor topics, consumers, schema registry
- **RabbitMQ**: http://localhost:15672 (guest/guest) - Monitor Celery tasks
- **Logs**: `docker-compose logs -f <service-name>`

## 🚢 Production Deployment

### Split into Separate Repositories

```bash
# Create separate repos for each service
github.com/yourcompany/smartcourse-lms
github.com/yourcompany/smartcourse-ai
github.com/yourcompany/smartcourse-analytics
github.com/yourcompany/smartcourse-notification
```

### Kubernetes Deployment

Each service gets its own deployment:
- LMS: 3 replicas
- AI: 2 replicas (GPU nodes)
- Analytics: 2 replicas
- Notification: 1 worker

### CI/CD Pipeline

```yaml
# Example GitHub Actions
- Build Docker image
- Push to container registry
- Deploy to Kubernetes
- Run database migrations
```

## 📖 Documentation

- [services/lms/README.md](services/lms/README.md) - LMS Service details
- [services/ai/README.md](services/ai/README.md) - AI Service details
- [services/analytics/README.md](services/analytics/README.md) - Analytics Service details
- [services/notification/README.md](services/notification/README.md) - Notification Service details
- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture documentation
- [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) - Modular monolith migration guide

## 🤝 Contributing

1. Choose a service to work on
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes in respective service folder
4. Test locally
5. Submit pull request

## 📝 License

MIT License - See LICENSE file for details

---

**Current Status**: 
- ✅ LMS Service: **Production Ready**
- 🚧 AI Service: **Skeleton (Ready for Implementation)**
- 🚧 Analytics Service: **Skeleton (Ready for Implementation)**
- 🚧 Notification Service: **Skeleton (Ready for Implementation)**

**Next Steps**: Implement AI, Analytics, and Notification services following the established patterns in LMS service.
