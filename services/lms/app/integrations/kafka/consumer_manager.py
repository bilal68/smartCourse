"""
Consumer manager for certificate generation (side effects only).
"""

import threading
import time

from app.core.logging import get_logger
from app.tasks.certificate_event_tasks import run_certificate_consumer

logger = get_logger(__name__)


class ConsumerManager:
    """Manages certificate consumer for side effects only."""
    
    def __init__(self):
        self.consumer_threads = []
        self.running = False
    
    def start_certificate_consumer(self):
        """Start certificate consumer for side effects."""
        logger.info("Starting certificate consumer...")
        
        self.running = True
        
        # Start certificate consumer (for course completion → certificate generation)
        cert_thread = threading.Thread(
            target=self._run_certificate_consumer,
            daemon=True,
            name="certificate-consumer"
        )
        cert_thread.start()
        self.consumer_threads.append(cert_thread)
        
        logger.info("Certificate consumer started for side effects")
    
    def _run_certificate_consumer(self):
        """Run certificate consumer with error recovery."""
        while self.running:
            try:
                logger.info("Starting certificate consumer thread...")
                run_certificate_consumer()
            except Exception as e:
                logger.error(f"Certificate consumer failed: {str(e)}", exc_info=True)
                if self.running:
                    logger.info("Restarting certificate consumer in 5 seconds...")
                    time.sleep(5)
                else:
                    break
    
    def stop_all_consumers(self):
        """Stop all consumers gracefully."""
        logger.info("Stopping consumers...")
        self.running = False
        
        for thread in self.consumer_threads:
            thread.join(timeout=5.0)
        
        logger.info("All consumers stopped")


# Global instance
consumer_manager = ConsumerManager()


def start_certificate_consumer():
    """Start certificate consumer only."""
    consumer_manager.start_certificate_consumer()


def stop_consumers():
    """Stop all consumers."""
    consumer_manager.stop_all_consumers()