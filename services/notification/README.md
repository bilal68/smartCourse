# Notification Service

Background worker service for sending notifications via email, SMS, and push notifications.

## Features (Planned)

- 📧 **Email Notifications** - SendGrid/SMTP integration
- 📱 **SMS Notifications** - Twilio integration
- 🔔 **Push Notifications** - Firebase/OneSignal integration
- 📬 **In-App Notifications** - Real-time notifications
- 📊 **Notification History** - Track sent notifications

## Architecture

```
app/
├── celery_app.py        # Celery worker (NO HTTP server)
├── tasks/
│   ├── email_tasks.py   # Email sending
│   ├── sms_tasks.py     # SMS sending
│   └── push_tasks.py    # Push notifications
├── templates/           # Email templates
├── core/               # Core utilities
└── integrations/
    ├── sendgrid/       # Email provider
    ├── twilio/         # SMS provider
    └── kafka/          # Kafka consumer
```

## Events Consumed

- `user.registered` → Send welcome email
- `course.published` → Notify subscribers
- `enrollment.created` → Send enrollment confirmation
- `enrollment.completed` → Send certificate email
- `assignment.graded` → Notify student

## No HTTP API

This service is a **background worker only**:
- ✅ Consumes Kafka events
- ✅ Processes Celery tasks
- ❌ No HTTP endpoints
- ❌ No database (uses LMS DB for user emails)

## Database

Uses LMS database for:
- User email addresses
- Notification preferences
- Notification delivery log
