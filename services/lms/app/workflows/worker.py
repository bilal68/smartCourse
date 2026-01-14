"""Temporal worker for running publish course workflows."""

import asyncio
import logging
import sys
from typing import Optional

# Ensure app is in path for imports
sys.path.insert(0, '/'.join(__file__.split('/')[:-3]))

from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config import settings
from app.core.logging import get_logger
from app.workflows.publish_course_workflow import (
    PublishCourseWorkflow,
    mark_course_processing,
    publish_to_kafka,
    wait_for_ai_processing,
    mark_course_ready,
    rollback_course_publish,
)

logger = get_logger(__name__)


class TemporalWorker:
    """Manages Temporal worker lifecycle."""
    
    def __init__(self):
        self.worker: Optional[Worker] = None
        self.client: Optional[Client] = None
        self.temporal_host = getattr(settings, "TEMPORAL_HOST", "localhost")
        self.temporal_port = getattr(settings, "TEMPORAL_PORT", 7233)
    
    async def start(self) -> None:
        """Start the Temporal worker."""
        try:
            # Connect to Temporal server
            self.client = await Client.connect(
                f"{self.temporal_host}:{self.temporal_port}"
            )
            logger.info(f"Connected to Temporal server at {self.temporal_host}:{self.temporal_port}")
            
            # Create worker with standalone activity functions
            self.worker = Worker(
                self.client,
                task_queue="course-publishing",
                workflows=[PublishCourseWorkflow],
                activities=[
                    mark_course_processing,
                    publish_to_kafka,
                    wait_for_ai_processing,
                    mark_course_ready,
                    rollback_course_publish,
                ],
            )
            
            # Start worker
            logger.info("Starting Temporal worker on task queue 'course-publishing'")
            await self.worker.run()
            
        except Exception as e:
            logger.error(f"Failed to start Temporal worker: {str(e)}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the Temporal worker."""
        if self.worker:
            logger.info("Stopping Temporal worker")
            self.worker.shutdown()
        if self.client:
            await self.client.aclose()


def run_worker() -> None:
    """Run the Temporal worker synchronously."""
    worker = TemporalWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker error: {str(e)}")
        raise


if __name__ == "__main__":
    run_worker()
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    run_worker()
