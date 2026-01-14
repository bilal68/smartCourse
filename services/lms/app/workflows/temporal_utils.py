"""Utilities for interacting with Temporal."""

import asyncio
from datetime import timedelta
from typing import Dict, Any, Optional
from uuid import UUID

from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


async def get_temporal_client() -> Client:
    """Get or create Temporal client."""
    temporal_host = getattr(settings, "TEMPORAL_HOST", "localhost")
    temporal_port = getattr(settings, "TEMPORAL_PORT", 7233)
    
    try:
        client = await Client.connect(f"{temporal_host}:{temporal_port}")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Temporal: {str(e)}")
        raise


async def start_publish_course_workflow(
    course_id: UUID,
    course_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Start the publish course workflow.
    
    Args:
        course_id: ID of the course to publish
        course_data: Course data to include in workflow
    
    Returns:
        Dictionary with workflow execution ID
    """
    try:
        client = await get_temporal_client()
        
        workflow_id = f"publish-course-{course_id}"
        
        # Start workflow execution with idempotency
        try:
            handle = await client.start_workflow(
                "PublishCourseWorkflow",
                args=[str(course_id), course_data],
                id=workflow_id,
                task_queue="course-publishing",
                execution_timeout=timedelta(minutes=5),
            )
        except WorkflowAlreadyStartedError:
            # Workflow already running, get existing handle
            logger.info(f"Workflow already running: {workflow_id}, returning existing handle")
            handle = client.get_workflow_handle(workflow_id)
            return {
                "workflow_id": handle.id,
                "workflow_run_id": handle.result_run_id,
                "status": "already_running"
            }
        
        logger.info(f"Started PublishCourseWorkflow: workflow_id={workflow_id}")
        
        return {
            "workflow_id": handle.id,
            "workflow_run_id": handle.result_run_id,
            "course_id": str(course_id)
        }
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {str(e)}", exc_info=True)
        raise


async def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get the status of a running workflow."""
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        
        try:
            # Try to get result (blocks if still running)
            result = await asyncio.wait_for(handle.result(), timeout=0.1)
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": result
            }
        except asyncio.TimeoutError:
            # Still running
            describe = await handle.describe()
            return {
                "workflow_id": workflow_id,
                "status": "running",
                "started_at": describe.start_time,
                "execution_timeout": describe.execution_timeout
            }
        except Exception as e:
            # Failed or canceled
            describe = await handle.describe()
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "started_at": describe.start_time
            }
    
    except Exception as e:
        logger.error(f"Failed to get workflow status: {str(e)}")
        raise


async def cancel_workflow(workflow_id: str) -> Dict[str, Any]:
    """Cancel a running workflow."""
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()
        
        logger.info(f"Cancelled workflow: workflow_id={workflow_id}")
        
        return {
            "workflow_id": workflow_id,
            "cancelled": True
        }
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {str(e)}")
        raise
