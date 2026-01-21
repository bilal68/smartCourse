#!/usr/bin/env python3
"""Debug script to manually signal a stuck Temporal workflow."""

import asyncio
import sys
import os

# Add LMS to path
sys.path.append('services/lms')
os.chdir('services/lms')

from app.workflows.temporal_utils import signal_ai_processing_done

async def signal_failure():
    """Signal the stuck workflow with failure to trigger rollback."""
    course_id = "fb750e3f-5f97-4bf0-9784-44eeb32e9a9d"
    
    print(f"🚨 Sending FAILURE signal to workflow: {course_id}")
    
    try:
        result = await signal_ai_processing_done(
            course_id=course_id,
            success=False,
            chunks_created=0,
            error_message="Manual debug signal - AI processing failed"
        )
        print(f"✅ Signal sent successfully: {result}")
    except Exception as e:
        print(f"❌ Failed to signal workflow: {e}")

if __name__ == "__main__":
    asyncio.run(signal_failure())