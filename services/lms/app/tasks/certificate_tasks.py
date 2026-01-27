from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.core.logging import get_logger

from app.models.certificate import Certificate
from app.modules.enrollments.models import Enrollment, EnrollmentStatus


logger = get_logger(__name__)


def _make_serial() -> str:
    return f"CERT-{uuid4().hex[:10].upper()}"


@celery_app.task(
    name="app.tasks.certificate_tasks.generate_certificate_for_enrollment",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_certificate_for_enrollment(self, enrollment_id: str) -> dict:
    """
    Generate a certificate after the course is completed.
    For now: creates a Certificate DB row with a dummy URL.
    Later: replace URL generation with real PDF render + S3 upload.
    """
    db: Session = SessionLocal()
    try:
        enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if not enrollment:
            return {"ok": False, "reason": "enrollment_not_found"}

        # Must be completed to issue certificate (guard)
        if enrollment.status != EnrollmentStatus.completed:
            return {"ok": False, "reason": "enrollment_not_completed"}

        # Idempotency: don't generate twice
        existing = (
            db.query(Certificate)
            .filter(Certificate.enrollment_id == enrollment.id)
            .first()
        )
        if existing:
            return {
                "ok": True,
                "already_exists": True,
                "certificate_id": str(existing.id),
                "certificate_url": existing.certificate_url,
            }

        issued_at = datetime.utcnow()
        serial = _make_serial()

        # Placeholder URL (swap later with S3 URL)
        cert_url = f"https://example.com/certificates/{serial}.pdf"

        cert = Certificate(
            id=uuid4(),
            enrollment_id=enrollment.id,
            serial_no=serial,
            certificate_url=cert_url,
            issued_at=issued_at,
        )

        db.add(cert)
        db.commit()
        db.refresh(cert)

        logger.info(
            "certificate generated",
            enrollment_id=str(enrollment.id),
            certificate_id=str(cert.id),
            serial_no=serial,
        )

        # Trigger email in background (optional)
        try:
            from app.tasks.notification_tasks import send_certificate_email

            send_certificate_email.delay(
                enrollment_id=str(enrollment.id),
                certificate_url=cert.certificate_url,
                serial_no=cert.serial_no,
            )
        except Exception:
            # Don't fail the certificate task if email task import/call fails
            logger.exception("failed to enqueue send_certificate_email")

        return {
            "ok": True,
            "certificate_id": str(cert.id),
            "certificate_url": cert.certificate_url,
            "serial_no": cert.serial_no,
        }
    finally:
        db.close()
