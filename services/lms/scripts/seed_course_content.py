#!/usr/bin/env python3
"""
Seed course content to MinIO/S3 for testing and development.
Uses the S3Client directly to upload JSON content for specific courses.

Usage:
    python scripts/seed_course_content.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.s3_client import get_s3_client
from app.db.session import SessionLocal
from app.modules.courses.models import Course, Module, LearningAsset, AssetStatus, CourseStatus
from app.modules.auth.models import User  # Import User to resolve relationship
from app.modules.enrollments.models import Enrollment  # Import Enrollment to resolve relationship
from app.core.logging import get_logger

logger = get_logger(__name__)


# Sample content templates
INTRO_CONTENT = {
    "schema": "smartcourse.editor.v1",
    "doc": {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Introduction to the Course"}]
            },
            {
                "type": "paragraph",
                "content": [{
                    "type": "text",
                    "text": "Welcome to this comprehensive course! This module will introduce you to the fundamental concepts and set you up for success. You'll learn the core principles, best practices, and gain hands-on experience through practical exercises and real-world examples."
                }]
            },
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "What You'll Learn"}]
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Core principles and foundational knowledge"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Best practices and industry standards"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Hands-on exercises and practical applications"}]
                        }]
                    }
                ]
            }
        ]
    }
}

ADVANCED_CONTENT = {
    "schema": "smartcourse.editor.v1",
    "doc": {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Advanced Concepts"}]
            },
            {
                "type": "paragraph",
                "content": [{
                    "type": "text",
                    "text": "In this advanced module, we'll dive deep into sophisticated topics and techniques. You'll explore complex scenarios, optimize your solutions, and master professional-grade implementations. This content builds on the foundations from previous modules and prepares you for real-world challenges."
                }]
            },
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Key Topics Covered"}]
            },
            {
                "type": "orderedList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Advanced design patterns and architectures"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Performance optimization techniques"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Security best practices and implementation"}]
                        }]
                    }
                ]
            },
            {
                "type": "codeBlock",
                "attrs": {"language": "python"},
                "content": [{
                    "type": "text",
                    "text": "# Example code snippet\ndef advanced_function(param):\n    \"\"\"Demonstrates advanced concepts\"\"\"\n    result = process_data(param)\n    return optimize(result)"
                }]
            }
        ]
    }
}


def seed_content_for_course(course_id: str, dry_run: bool = False):
    """
    Seed content for all assets in a specific course.
    
    Args:
        course_id: UUID of the course
        dry_run: If True, only print what would be done without uploading
    """
    db = SessionLocal()
    s3_client = get_s3_client()
    
    try:
        # Get course with modules and assets
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            logger.error(f"Course {course_id} not found")
            return
        
        logger.info(f"Seeding content for course: {course.title} ({course.id})")
        
        for module in course.modules:
            logger.info(f"  Module: {module.title}")
            
            for asset in module.assets:
                # Handle different asset types
                if asset.asset_type.value == "article":
                    # Process article assets with content upload
                    process_article = True
                    
                    # Check if we need to update source_url for existing content
                    needs_update = (asset.status == AssetStatus.ready and 
                                  asset.key and 
                                  asset.source_url != asset.key)
                    
                    if asset.status == AssetStatus.ready and not needs_update:
                        logger.info(f"    Skipping {asset.title} (already has correct content)")
                        continue
                        
                elif asset.asset_type.value in ["video", "pdf"]:
                    # For video/PDF assets, just fix dummy URLs to proper S3 keys
                    process_article = False
                    
                    # Check if it has dummy URLs that need fixing - be more specific
                    is_dummy_url = (asset.source_url and 
                                   ("example.com" in asset.source_url or 
                                    asset.source_url.startswith("https://example.com/")))
                    
                    logger.info(f"    Checking {asset.title} (type: {asset.asset_type.value})")
                    logger.info(f"    Current source_url: {asset.source_url}")
                    logger.info(f"    Is dummy URL: {is_dummy_url}")
                    
                    if not is_dummy_url:
                        logger.info(f"    Skipping {asset.title} (type: {asset.asset_type.value}) - no dummy URL to fix")
                        continue
                        
                    # Build proper S3 key for video/PDF
                    if asset.asset_type.value == "video":
                        extension = "mp4"  # Default video extension
                    else:  # PDF
                        extension = "pdf"
                    
                    key = f"courses/{course.id}/modules/{module.id}/assets/{asset.id}/content.{extension}"
                    
                    logger.info(f"    Fixing dummy URL for {asset.title} (type: {asset.asset_type.value})")
                    
                    if not dry_run:
                        # Update the source_url to the proper S3 key
                        asset.source_url = key
                        asset.bucket = s3_client.bucket
                        asset.key = key
                        # Don't change status since we're not uploading actual content
                        db.add(asset)
                        db.commit()
                        logger.info(f"    ✅ Fixed dummy URL: {asset.title}")
                    else:
                        logger.info(f"    [DRY RUN] Would fix URL to: {key}")
                    
                    continue
                    
                else:
                    logger.info(f"    Skipping {asset.title} (type: {asset.asset_type.value}) - unsupported type")
                    continue
                
                # For article assets, handle content upload
                if not process_article:
                    continue
                    
                # Check if we need to update source_url for existing article content
                needs_update = (asset.status == AssetStatus.ready and 
                              asset.key and 
                              asset.source_url != asset.key)
                
                # Choose content template based on asset order/position
                content = INTRO_CONTENT if asset.order_index == 0 else ADVANCED_CONTENT
                
                # Build S3 key
                key = s3_client.build_asset_key(course.id, module.id, asset.id)
                
                if dry_run:
                    logger.info(f"    [DRY RUN] Would upload to: {key}")
                    continue
                
                # If this is just a source_url update, don't re-upload content
                if needs_update:
                    logger.info(f"    Updating source_url for {asset.title}")
                    asset.source_url = asset.key
                    db.add(asset)
                    db.commit()
                    logger.info(f"    ✅ Updated source_url: {asset.title}")
                    continue
                
                # Upload new textual content to S3 (JSON format with text content)
                import json
                content_bytes = json.dumps(content, indent=2).encode('utf-8')
                
                try:
                    s3_client.client.put_object(
                        Bucket=s3_client.bucket,
                        Key=key,
                        Body=content_bytes,
                        ContentType='application/json'
                    )
                    
                    # Update asset in DB (textual content only, no course publishing)
                    import hashlib
                    asset.status = AssetStatus.ready
                    asset.bucket = s3_client.bucket
                    asset.key = key
                    asset.source_url = key  # Set source_url to the S3 key for AI service
                    asset.size_bytes = len(content_bytes)
                    asset.content_hash = hashlib.sha256(content_bytes).hexdigest()
                    asset.version = 1
                    asset.validation_error = None
                    
                    db.add(asset)
                    db.commit()
                    
                    logger.info(f"    ✅ Uploaded textual content: {asset.title} ({len(content_bytes)} bytes)")
                    
                except Exception as e:
                    logger.error(f"    ❌ Failed to upload {asset.title}: {e}")
                    db.rollback()
        
        logger.info(f"✅ Content seeding completed for course {course.title} (content creation only, no publishing)")
        
    finally:
        db.close()


def seed_all_draft_courses(dry_run: bool = False):
    """Seed content for all courses in draft status"""
    db = SessionLocal()
    
    try:
        from app.modules.courses.models import CourseStatus
        courses = db.query(Course).filter(Course.status == CourseStatus.draft).all()
        
        logger.info(f"Found {len(courses)} draft courses to seed")
        
        for course in courses:
            seed_content_for_course(str(course.id), dry_run=dry_run)
        
    finally:
        db.close()


def fix_all_dummy_urls(dry_run: bool = False):
    """Fix all existing dummy URLs across all courses"""
    db = SessionLocal()
    s3_client = get_s3_client()
    
    try:
        # Find all assets with dummy URLs
        all_assets = db.query(LearningAsset).filter(
            LearningAsset.source_url.ilike('%example.com%')
        ).all()
        
        logger.info(f"Found {len(all_assets)} assets with dummy URLs to fix")
        
        for asset in all_assets:
            logger.info(f"Fixing {asset.title} ({asset.asset_type.value}): {asset.source_url}")
            
            if asset.asset_type.value == "video":
                extension = "mp4"
            elif asset.asset_type.value == "pdf":  
                extension = "pdf"
            else:
                logger.info(f"  Skipping unsupported type: {asset.asset_type.value}")
                continue
                
            # Build proper S3 key
            proper_key = f"courses/{asset.module.course_id}/modules/{asset.module_id}/assets/{asset.id}/content.{extension}"
            
            if dry_run:
                logger.info(f"  [DRY RUN] Would fix to: {proper_key}")
            else:
                asset.source_url = proper_key
                asset.bucket = s3_client.bucket
                asset.key = proper_key
                db.add(asset)
                logger.info(f"  ✅ Fixed to: {proper_key}")
        
        if not dry_run:
            db.commit()
            logger.info("✅ All dummy URLs fixed!")
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed course content to MinIO/S3")
    parser.add_argument("--course-id", help="Specific course ID to seed")
    parser.add_argument("--all", action="store_true", help="Seed all draft courses")
    parser.add_argument("--fix-urls", action="store_true", help="Fix all existing dummy URLs")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without uploading")
    
    args = parser.parse_args()
    
    if args.course_id:
        seed_content_for_course(args.course_id, dry_run=args.dry_run)
    elif args.all:
        seed_all_draft_courses(dry_run=args.dry_run)
    elif args.fix_urls:
        fix_all_dummy_urls(dry_run=args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)
