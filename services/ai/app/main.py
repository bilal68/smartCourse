from fastapi import FastAPI
import threading
import time

from app.core.logging import configure_logging, get_logger
from app.integrations.kafka.client import get_kafka_consumer
from app.integrations.kafka.handlers import get_content_handler
from app.modules.content.routes import router as content_router
from app.modules.search.routes import router as search_router
from app.modules.rag.routes import router as rag_router

# Configure logging
configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="SmartCourse AI Service",
    description="AI-powered features for course content processing and recommendations",
    version="1.0.0"
)

# Include API routes
app.include_router(content_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")


def start_kafka_consumer():
    """Start Kafka consumer in a separate thread."""
    time.sleep(2)  # Wait for FastAPI to start
    
    consumer = get_kafka_consumer()
    content_handler = get_content_handler()
    
    # Register event handlers
    consumer.register_handler("course.published", content_handler.handle_course_published)
    
    # Start consuming
    consumer.start_consuming()


@app.on_event("startup")
async def startup_event():
    """Start background services."""
    logger.info("Starting AI service...")
    
    # Start Kafka consumer in background thread
    kafka_thread = threading.Thread(target=start_kafka_consumer, daemon=True)
    kafka_thread.start()
    
    logger.info("AI service started with Kafka consumer")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-service"}

@app.get("/")
async def root():
    return {
        "service": "SmartCourse AI Service",
        "version": "1.0.0",
        "status": "🚀 Running with Content Processing"
    }

# Content processing endpoints
@app.get("/api/v1/processing/status")
async def processing_status():
    """Get processing service status."""
    return {
        "service": "content-processing",
        "status": "active",
        "capabilities": ["content_chunking", "text_analysis"]
    }
