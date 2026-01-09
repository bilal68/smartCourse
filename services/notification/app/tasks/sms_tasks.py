from app.celery_app import celery_app

@celery_app.task(name="notification.send_sms")
def send_sms(phone: str, message: str):
    """
    Send SMS notification via Twilio.
    """
    print(f"📱 Sending SMS to {phone}: {message}")
    # TODO: Implement Twilio integration
    return {"status": "sent", "to": phone}
