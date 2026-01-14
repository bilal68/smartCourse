#!/usr/bin/env python
"""
Script to generate dummy content files for course assets.

Generates realistic dummy content (articles, transcripts, PDFs) and stores them in S3.
Content processing/chunking is handled separately by the AI service.

Usage:
    python -m app.scripts.generate_course_content <course_id> [generate_dummy]
    
Examples:
    # Generate dummy content for a course
    python -m app.scripts.generate_course_content a39b32f4-76c0-47dc-a0be-22b739301611
    
    # Skip dummy generation (just mark as ready)
    python -m app.scripts.generate_course_content a39b32f4-76c0-47dc-a0be-22b739301611 false
"""

import sys
from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.modules.courses.models import Course, Module, CourseProcessingStatus
from app.modules.auth.models import User  # Import User to register the model
from app.modules.enrollments.models import Enrollment  # Import Enrollment to register the model
from app.modules.courses.dummy_content import DummyContentGenerator
from app.core.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)


def generate_course_content(course_id: str, generate_dummy: bool = True) -> bool:
    """
    Generate dummy content files for a course (LMS responsibility only).
    Content processing/chunking is handled by the AI service.
    
    Args:
        course_id: UUID of course to process
        generate_dummy: Whether to generate dummy content (default: True)
        
    Returns:
        True if successful, False otherwise
    """
    db = SessionLocal()
    
    try:
        logger.info(f"🎯 Loading course: {course_id}")
        
        # Load course with all modules and assets (skip instructor to avoid User import issues)
        course = (
            db.query(Course)
            .options(
                joinedload(Course.modules).joinedload(Module.assets)
            )
            .filter(Course.id == course_id)
            .first()
        )
        
        if not course:
            logger.error(f"❌ Course not found: {course_id}")
            return False
        
        logger.info(f"✅ Loaded course: {course.title}")
        
        # Update status to processing
        course.processing_status = CourseProcessingStatus.processing
        course.processing_error = None
        db.commit()
        logger.info(f"📝 Status set to: {CourseProcessingStatus.processing.value}")
        
        # Step 1: Generate or validate content
        if generate_dummy:
            logger.info("🔨 Generating dummy content for all assets...")
            generator = DummyContentGenerator(db)
            gen_stats = generator.generate_for_course(course)
            
            logger.info("✅ Dummy content generation complete:")
            logger.info(f"   Modules: {gen_stats['modules_processed']}")
            logger.info(f"   Assets: {gen_stats['assets_processed']}")
            logger.info(f"   Files: {gen_stats['files_created']}")
            logger.info(f"   Size: {gen_stats['total_content_size']} bytes")
        else:
            logger.info("⏭️  Using existing content (skipping dummy generation)")
        
        # Step 2: Content processing is handled by AI service
        logger.info("📤 Content generation complete - AI service will handle processing")
        
        # Mark course as ready (AI service will process content separately)
        course.processing_status = CourseProcessingStatus.ready
        course.processing_error = None
        course.processed_at = datetime.utcnow()
        db.commit()
        
        logger.info("✅ Course marked as READY for AI service processing")
        logger.info(f"🎉 Content generation completed successfully!")
        logger.info(f"   Course Status: {course.processing_status.value}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to generate content: {str(e)}", exc_info=True)
        
        # Try to mark course as failed
        try:
            course = db.query(Course).filter(Course.id == course_id).first()
            if course:
                course.processing_status = CourseProcessingStatus.failed
                course.processing_error = f"Generation error: {str(e)}"
                course.processed_at = datetime.utcnow()
                db.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update course status: {str(commit_error)}")
        
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    course_id = sys.argv[1]
    generate_dummy = True
    
    if len(sys.argv) > 2:
        generate_dummy = sys.argv[2].lower() not in ("false", "0", "no")
    
    # Run the content generation
    success = generate_course_content(course_id, generate_dummy)
    sys.exit(0 if success else 1)
