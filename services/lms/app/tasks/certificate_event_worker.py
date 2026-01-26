from app.celery_app import celery_app
from app.tasks.certificate_tasks import generate_certificate_for_enrollment
from app.integrations.kafka.consumer_manager import ConsumerManager

@celery_app.task(name="app.tasks.certificate_event_worker.run_certificate_consumer")
def run_certificate_consumer():
    """
    Run the Kafka consumer for course completion events and trigger certificate generation as a Celery task.
    This should be started as a separate Celery worker process.
    """
    manager = ConsumerManager()
    manager.start_certificate_consumer()
    # The consumer manager will run indefinitely, listening for events
