"""Event handlers for AI service."""

from typing import Dict, Any
from datetime import datetime
from uuid import UUID

from app.content.processor import ContentProcessor
from app.integrations.kafka.client import get_kafka_producer
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.processing_job import ProcessingJob, ProcessingStatus
from app.models.content_chunk import ContentChunk
from app.models.course_analysis import CourseAnalysis

logger = get_logger(__name__)


class ContentProcessingHandler:
    """Handles content processing events from course publishing."""
    
    def __init__(self):
        self.processor = ContentProcessor()
        self.kafka_producer = get_kafka_producer()
    
    def handle_course_published(self, event: Dict[str, Any]):
        """Handle course.published event - trigger content processing."""
        try:
            logger.info(f"🎯 Raw event received: {event}")
            
            # Extract course_id and course_data from nested payload structure
            # LMS outbox events have structure: {event_type, aggregate_id, payload: {course_id, course_data}}
            course_id = None
            course_data = {}
            
            # Try different possible structures
            if 'payload' in event:
                # Outbox event structure
                payload = event['payload']
                course_id = payload.get('course_id') or event.get('aggregate_id')
                course_data = payload.get('course_data', {})
            else:
                # Direct event structure  
                course_id = event.get('course_id') or event.get('aggregate_id')
                course_data = event.get('course_data', {})
            
            logger.info(f"🎯 Extracted: course_id={course_id}, assets_count={len(course_data.get('assets', []))}")
            
            # Validate course_id
            if not course_id:
                logger.error("❌ No course_id found in event payload")
                logger.error(f"❌ Available keys: {list(event.keys())}")
                return
                
            # Convert course_id to UUID if it's a string
            from uuid import UUID
            try:
                if isinstance(course_id, str):
                    course_id = UUID(course_id)
                    logger.info(f"✅ Converted course_id to UUID: {course_id}")
            except ValueError as ve:
                logger.error(f"❌ Invalid course_id format: {course_id}, error: {str(ve)}")
                return
            
            # FULL PROCESSING PIPELINE (now enabled)
            logger.info(f"🔧 Testing database connection...")
            
            # ===== DATABASE PROCESSING =====
            from app.models.processing_job import ProcessingJob, ProcessingStatus
            from app.models.content_chunk import ContentChunk
            from app.content.processor import ContentProcessor
            from datetime import datetime
            from sqlalchemy import text
            
            db = SessionLocal()
            try:
                # Test database connection first
                result = db.execute(text("SELECT current_database()"))
                current_db = result.fetchone()[0]
                logger.info(f"🔧 Connected to database: {current_db}")
                # Test if processing_jobs table exists
                result = db.execute(text("SELECT COUNT(*) FROM processing_jobs"))
                count = result.fetchone()[0]
                logger.info(f"🔧 processing_jobs table has {count} rows")

                # UPSERT: Find existing ProcessingJob or create new
                processing_job = db.query(ProcessingJob).filter(ProcessingJob.course_id == course_id).first()
                if processing_job:
                    logger.info(f"🔄 Updating existing ProcessingJob for course_id={course_id}")
                    processing_job.status = ProcessingStatus.PROCESSING
                    processing_job.total_assets = len(course_data.get('assets', []))
                    processing_job.created_at = datetime.utcnow()
                else:
                    logger.info(f"🆕 Creating new ProcessingJob for course_id={course_id}")
                    processing_job = ProcessingJob(
                        course_id=course_id,
                        status=ProcessingStatus.PROCESSING,
                        total_assets=len(course_data.get('assets', [])),
                        created_at=datetime.utcnow()
                    )
                    db.add(processing_job)
                db.commit()

                # Process content using ContentProcessor
                processor = ContentProcessor()
                processing_result = processor.process_course_assets(course_data)

                # Store content chunks in database
                self._store_processing_results(db, str(course_id), processing_result)

                # Determine if processing was actually successful
                successful_assets = processing_result['successful']
                total_assets = processing_result['total_assets']
                
                # Consider processing failed if NO assets were successfully processed
                if successful_assets == 0:
                    processing_job.status = ProcessingStatus.FAILED
                    error_msg = f"All {total_assets} assets failed to process"
                    processing_job.error_message = error_msg
                    
                    status_event = {
                        "course_id": str(course_id),
                        "status": "failed",
                        "processed_assets": 0,
                        "failed_assets": processing_result['failed'],
                        "total_chunks": 0,
                        "error_message": error_msg
                    }
                else:
                    # At least some assets processed successfully
                    processing_job.status = ProcessingStatus.COMPLETED
                    
                    status_event = {
                        "course_id": str(course_id),
                        "status": "completed",
                        "processed_assets": processing_result['successful'],
                        "failed_assets": processing_result['failed'],
                        "total_chunks": processing_result['total_chunks'],
                        "error_message": None
                    }
                
                processing_job.processed_assets = processing_result['successful']
                processing_job.failed_assets = processing_result['failed']
                processing_job.total_chunks_created = processing_result['total_chunks']
                processing_job.completed_at = datetime.utcnow()
                db.commit()
            except Exception as db_error:
                logger.error(f"💥 Database error: {str(db_error)}", exc_info=True)
                # Send error response
                status_event = {
                    "course_id": str(course_id),
                    "status": "failed",
                    "processed_assets": 0,
                    "failed_assets": len(course_data.get('assets', [])),
                    "total_chunks": 0,
                    "error_message": f"Database error: {str(db_error)}"
                }
            finally:
                db.close()
            
            # ===== SIMPLIFIED VERSION (now disabled) =====
            # logger.info(f"🚀 Would process course with {len(course_data.get('assets', []))} assets")
            # 
            # # Send a simple test response
            # status_event = {
            #     "course_id": str(course_id),
            #     "status": "completed",
            #     "processed_assets": len(course_data.get('assets', [])),
            #     "failed_assets": 0,
            #     "total_chunks": 0,
            #     "error_message": None
            # }
            
            # Publish success or failure event based on status
            if status_event["status"] == "completed":
                self.kafka_producer.publish_content_processed(str(course_id), status_event)
                logger.info(f"✅ Published completion event for course_id={course_id}")
            else:
                # Publish failure event using proper function
                from app.integrations.kafka.producer import publish_course_failure
                publish_course_failure(str(course_id), status_event["error_message"])
                logger.info(f"❌ Published failure event for course_id={course_id}")
            
        except Exception as e:
            logger.error(f"💥 Error in handle_course_published: {str(e)}", exc_info=True)
            # Publish failure event for any unexpected errors
            from app.integrations.kafka.producer import publish_course_failure  
            publish_course_failure(str(course_id), str(e))

    def _store_processing_results(self, db, course_id: str, results: Dict[str, Any]):
        """
        Store processing results in AI database.
        
        This method would be called in the full pipeline to:
        1. Delete existing chunks for this course (reprocessing)
        2. Store new content chunks with embeddings
        3. Generate course analysis using AI
        """
        from app.models.content_chunk import ContentChunk
        from app.models.course_analysis import CourseAnalysis
        from uuid import UUID
        
        course_uuid = UUID(course_id)
        
        # Delete existing chunks for this course (in case of reprocessing)
        db.query(ContentChunk).filter(ContentChunk.course_id == course_uuid).delete()
        
        # Store new content chunks
        total_stored = 0
        for asset_id, chunks in results.get('chunks_by_asset', {}).items():
            for chunk_data in chunks:
                chunk = ContentChunk(
                    course_id=course_uuid,
                    asset_id=chunk_data['asset_id'],
                    chunk_index=chunk_data['chunk_index'],
                    content=chunk_data['chunk_text'],  # Use content field instead of chunk_text
                    start_char=chunk_data.get('start_char'),
                    end_char=chunk_data.get('end_char'), 
                    char_count=chunk_data.get('char_count')
                    # Note: token_count, embeddings, extra fields removed temporarily
                    # These need to be added back via migrations
                )
                db.add(chunk)
                total_stored += 1
        
        db.commit()
        logger.info(f"Stored {total_stored} content chunks in AI database, course_id={course_id}")
        
        # Generate and store course analysis
        self._generate_course_analysis(db, course_uuid, results)

    def _generate_course_analysis(self, db, course_id: UUID, results: Dict[str, Any]):
        """Generate AI-powered course analysis and insights."""
        from app.models.course_analysis import CourseAnalysis
        from datetime import datetime
        
        # This would integrate with AI models to analyze course content
        # For now, create a placeholder analysis
        
        analysis_data = {
            "summary": "AI-generated course summary would go here",
            "key_topics": ["Topic 1", "Topic 2", "Topic 3"],  # Extracted by AI
            "difficulty_score": 7.5,  # Calculated by AI model
            "estimated_duration": "2-3 hours"  # Based on content length
        }
        
        # Upsert (update or insert)
        existing = db.query(CourseAnalysis).filter(
            CourseAnalysis.course_id == course_id
        ).first()
        
        if existing:
            # Update existing analysis; SQLAlchemy will auto-set updated_at via onupdate
            existing.summary = analysis_data["summary"]
            existing.key_topics = analysis_data["key_topics"]
            existing.difficulty_score = analysis_data["difficulty_score"]
            existing.estimated_duration = analysis_data["estimated_duration"]
            existing.updated_at = datetime.utcnow()  # Explicitly set updated_at
        else:
            # Create new analysis
            analysis = CourseAnalysis(
                course_id=course_id,
                summary=analysis_data["summary"],
                key_topics=analysis_data["key_topics"],
                difficulty_score=analysis_data["difficulty_score"],
                estimated_duration=analysis_data["estimated_duration"]
            )
            db.add(analysis)
        
        db.commit()
        logger.info(f"Generated course analysis, course_id={course_id}")


# Global handler instance
_content_handler = None


def get_content_handler() -> ContentProcessingHandler:
    """Get the global content processing handler."""
    global _content_handler
    if _content_handler is None:
        _content_handler = ContentProcessingHandler()
    return _content_handler