# Analytics Service

Real-time analytics and reporting for learning metrics, course performance, and user engagement.

## Features (Planned)

- 📊 **Learning Analytics** - Track student progress and engagement
- 📈 **Course Performance** - Analyze course effectiveness
- 🎯 **Completion Metrics** - Track completion rates
- ⏱️ **Time Analytics** - Analyze learning time patterns
- 📉 **Trend Analysis** - Identify learning trends

## Architecture

```
app/
├── main.py              # FastAPI application
├── celery_app.py        # Celery for background aggregation
├── modules/
│   ├── metrics/        # Real-time metrics
│   ├── reports/        # Report generation
│   ├── dashboards/     # Dashboard data
│   └── aggregation/    # Data aggregation
├── core/               # Core utilities
├── db/                 # Time-series database (ClickHouse/TimescaleDB)
└── integrations/
    └── kafka/          # Kafka consumer for events
```

## Events Consumed

- `enrollment.created` → Track new enrollment
- `asset.completed` → Track asset completion
- `course.published` → Track course metrics
- `user.activity` → Track user engagement

## API Endpoints (Planned)

- `GET /api/v1/analytics/user/{id}` - User learning analytics
- `GET /api/v1/analytics/course/{id}` - Course performance metrics
- `GET /api/v1/analytics/completion-rates` - Overall completion rates
- `GET /api/v1/analytics/engagement` - Engagement metrics
- `POST /api/v1/analytics/track` - Track custom events

## Database

- **user_metrics** - User engagement metrics
- **course_metrics** - Course performance data
- **completion_events** - Completion tracking
- **time_tracking** - Learning time data
- **aggregated_stats** - Pre-computed statistics
