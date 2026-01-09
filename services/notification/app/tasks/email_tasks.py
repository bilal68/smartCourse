from app.celery_app import celery_app

@celery_app.task(name="notification.send_email")
def send_email(to: str, subject: str, template: str, context: dict):
    """
    Send email notification.
    
    Triggered by:
    - user.registered event
    - enrollment.created event
    - course.published event
    """
    print(f"📧 Sending email to {to}: {subject}")
    # TODO: Implement SendGrid/SMTP integration
    return {"status": "sent", "to": to}


@celery_app.task(name="notification.send_welcome_email")
def send_welcome_email(user_id: str, email: str, name: str):
    """Send welcome email to new user."""
    print(f"👋 Sending welcome email to {name} ({email})")
    # TODO: Use email template
    return send_email(
        to=email,
        subject="Welcome to SmartCourse!",
        template="welcome.html",
        context={"name": name}
    )


@celery_app.task(name="notification.send_enrollment_confirmation")
def send_enrollment_confirmation(user_id: str, email: str, course_title: str):
    """Send enrollment confirmation email."""
    print(f"✅ Sending enrollment confirmation to {email} for {course_title}")
    return send_email(
        to=email,
        subject=f"Enrolled in {course_title}",
        template="enrollment.html",
        context={"course_title": course_title}
    )


@celery_app.task(name="notification.send_certificate_email")
def send_certificate_email(user_id: str, email: str, course_title: str, certificate_url: str):
    """Send certificate completion email."""
    print(f"🎓 Sending certificate to {email} for {course_title}")
    return send_email(
        to=email,
        subject=f"Certificate for {course_title}",
        template="certificate.html",
        context={
            "course_title": course_title,
            "certificate_url": certificate_url
        }
    )
