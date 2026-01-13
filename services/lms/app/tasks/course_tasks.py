"""Celery tasks for course content processing."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.core.logging import get_logger

from app.modules.courses.models import Course, CourseProcessingStatus, Module, LearningAsset
from app.modules.courses.dummy_content import DummyContentGenerator
from app.modules.courses.content_processor import ContentProcessor

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.course_tasks.process_course_content",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_course_content(self, course_id: str, use_dummy_content: bool = True) -> dict:
    """
    Process course content after publishing:
    1. Generate/validate content exists
    2. Chunk content for search
    3. Update processing status
    
    Args:
        course_id: UUID of course to process
        use_dummy_content: If True, generate dummy content. If False, assume content already uploaded.
        
    Returns:
        dict with processing results
    """
    db: Session = SessionLocal()
    
    try:
        logger.info(
            "Starting course content processing",
            course_id=course_id,
            use_dummy_content=use_dummy_content
        )
        
        # Fetch course with all modules and assets
        course = (
            db.query(Course)
            .options(
                joinedload(Course.modules).joinedload(Module.assets)
            )
            .filter(Course.id == course_id)
            .first()
        )
        
        if not course:
            logger.error("Course not found", course_id=course_id)
            return {"ok": False, "reason": "course_not_found"}
        
        # Update status to processing
        course.processing_status = CourseProcessingStatus.processing
        course.processing_error = None
        db.commit()
        
        logger.info("Course status set to processing", course_id=course_id)
        
        # Step 1: Generate or validate content
        if use_dummy_content:
            logger.info("Generating dummy content", course_id=course_id)
            generator = DummyContentGenerator(db)
            gen_stats = generator.generate_for_course(course)
            logger.info("Dummy content generated", **gen_stats)
        else:
            logger.info("Using pre-uploaded content", course_id=course_id)
            # Validate that all assets have source_url
            missing_content = []
            for module in course.modules:
                for asset in module.assets:
                    if not asset.source_url:
                        missing_content.append({
                            "module": module.title,
                            "asset": asset.title
                        })
            
            if missing_content:
                error_msg = f"Assets missing content: {missing_content}"
                logger.error("Content validation failed", course_id=course_id, missing=missing_content)
                course.processing_status = CourseProcessingStatus.failed
                course.processing_error = error_msg
                course.processed_at = datetime.utcnow()
                db.commit()
                return {
                    "ok": False,
                    "reason": "missing_content",
                    "missing_assets": missing_content
                }
        
        # Step 2: Process and chunk content
        logger.info("Starting content chunking", course_id=course_id)
        processor = ContentProcessor(db)
        
        # Collect all assets from all modules
        all_assets = []
        for module in course.modules:
            all_assets.extend(module.assets)
        
        # Process all assets
        proc_stats = processor.process_course_assets(course.id, all_assets)
        
        # Check if any assets failed
        if proc_stats["failed"] > 0:
            error_msg = f"Failed to process {proc_stats['failed']} assets. See logs for details."
            logger.warning(
                "Some assets failed processing",
                course_id=course_id,
                failed_count=proc_stats["failed"],
                failed_assets=proc_stats["failed_assets"]
            )
            
            # Still mark as ready if at least some succeeded (partial success)
            if proc_stats["successful"] > 0:
                course.processing_status = CourseProcessingStatus.ready
                course.processing_error = error_msg
                course.processed_at = datetime.utcnow()
                db.commit()
                
                logger.info(
                    "Course processing completed with partial success",
                    course_id=course_id,
                    successful=proc_stats["successful"],
                    failed=proc_stats["failed"]
                )
                
                return {
                    "ok": True,
                    "status": "partial_success",
                    "processing_stats": proc_stats
                }
            else:
                # All failed
                course.processing_status = CourseProcessingStatus.failed
                course.processing_error = error_msg
                course.processed_at = datetime.utcnow()
                db.commit()
                
                logger.error("All assets failed processing", course_id=course_id)
                
                return {
                    "ok": False,
                    "reason": "all_assets_failed",
                    "processing_stats": proc_stats
                }
        
        # Success - all assets processed
        course.processing_status = CourseProcessingStatus.ready
        course.processing_error = None
        course.processed_at = datetime.utcnow()
        db.commit()
        
        logger.info(
            "Course processing completed successfully",
            course_id=course_id,
            **proc_stats
        )
        
        return {
            "ok": True,
            "status": "success",
            "processing_stats": proc_stats
        }
        
    except Exception as e:
        logger.error(
            "Course processing failed with exception",
            course_id=course_id,
            error=str(e),
            exc_info=True
        )
        
        # Update course status to failed
        try:
            course = db.query(Course).filter(Course.id == course_id).first()
            if course:
                course.processing_status = CourseProcessingStatus.failed
                course.processing_error = f"Processing error: {str(e)}"
                course.processed_at = datetime.utcnow()
                db.commit()
        except Exception as commit_error:
            logger.error(
                "Failed to update course status after error",
                course_id=course_id,
                error=str(commit_error)
            )
        
        # Re-raise for Celery retry mechanism
        raise
        
    finally:
        db.close()
