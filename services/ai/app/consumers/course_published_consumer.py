"""
Kafka consumer for course.published events.

Ingests course content, creates chunks, generates embeddings, stores in DB,
then publishes completion/failure event.
"""
import json
from typing import Dict, Any, List
from uuid import UUID

from kafka import KafkaConsumer
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.content_chunk import ContentChunk
from app.models.chunk_embedding import ChunkEmbedding
from app.services.chunking_service import get_chunking_service, TextChunk
from app.services.embedding_service import get_embedding_service
from app.kafka.producer import publish_course_completion, publish_course_failure
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CoursePublishedConsumer:
    """Consumer for course.published events."""
    
    def __init__(self):
        self.chunking_service = get_chunking_service()
        self.embedding_service = get_embedding_service()
    
    def process_event(self, event: Dict[str, Any]) -> None:
        """
        Main processing logic for course.published event.
        
        Steps:
        1. Extract course_id and assets from event
        2. For each asset, fetch content and create chunks
        3. Store chunks in content_chunks table
        4. Generate embeddings for each chunk
        5. Store embeddings in chunk_embeddings table
        6. Publish course.processing_completed event
        
        On error, publishes course.processing_failed event.
        """
        course_id = event.get("aggregate_id") or event.get("payload", {}).get("course_id")
        
        if not course_id:
            logger.error("No course_id in event payload")
            return
        
        try:
            course_id_uuid = UUID(course_id)
            logger.info(f"Processing course.published for course_id={course_id}")
            
            # Extract payload
            payload = event.get("payload", {})
            course_data = payload.get("course_data", {})
            assets = course_data.get("assets", [])
            
            if not assets:
                logger.warning(f"No assets found for course {course_id}")
                publish_course_completion(
                    course_id=course_id,
                    total_chunks_created=0,
                    total_embeddings_created=0,
                    processed_assets=0
                )
                return
            
            # Process all assets
            total_chunks = 0
            total_embeddings = 0
            
            db: Session = SessionLocal()
            try:
                # Delete old chunks/embeddings if re-publishing (idempotency)
                self._cleanup_old_data(db, course_id_uuid)
                
                for asset in assets:
                    asset_id = UUID(asset["id"])
                    asset_type = asset.get("asset_type", "article")
                    
                    logger.info(f"Processing asset {asset_id}, type={asset_type}")
                    
                    # Fetch content (simplified - assume we have text)
                    content = self._fetch_asset_content(asset)
                    
                    if not content:
                        logger.warning(f"No content for asset {asset_id}")
                        continue
                    
                    # Chunk the content
                    chunks = self.chunking_service.chunk_text(content)
                    
                    if not chunks:
                        logger.warning(f"No chunks created for asset {asset_id}")
                        continue
                    
                    # Store chunks in DB
                    chunk_ids = self._store_chunks(
                        db, course_id_uuid, asset_id, chunks
                    )
                    total_chunks += len(chunk_ids)
                    
                    # Generate and store embeddings
                    embeddings_created = self._generate_and_store_embeddings(
                        db, course_id_uuid, chunk_ids, chunks
                    )
                    total_embeddings += embeddings_created
                
                db.commit()
                logger.info(
                    f"Successfully processed course {course_id}: "
                    f"{total_chunks} chunks, {total_embeddings} embeddings"
                )
                
                # Publish success event
                publish_course_completion(
                    course_id=course_id,
                    total_chunks_created=total_chunks,
                    total_embeddings_created=total_embeddings,
                    processed_assets=len(assets)
                )
                
            except Exception as e:
                db.rollback()
                logger.exception(f"Error processing course {course_id}")
                publish_course_failure(course_id, str(e))
                
            finally:
                db.close()
                
        except Exception as e:
            logger.exception(f"Fatal error processing event: {e}")
            if course_id:
                publish_course_failure(course_id, str(e))
    
    def _cleanup_old_data(self, db: Session, course_id: UUID) -> None:
        """Delete old chunks/embeddings for idempotency."""
        # Embeddings will cascade delete via FK
        deleted_embeddings = db.query(ChunkEmbedding).filter(
            ChunkEmbedding.course_id == course_id
        ).delete()
        
        deleted_chunks = db.query(ContentChunk).filter(
            ContentChunk.course_id == course_id
        ).delete()
        
        if deleted_chunks > 0 or deleted_embeddings > 0:
            logger.info(
                f"Cleaned up old data: {deleted_chunks} chunks, "
                f"{deleted_embeddings} embeddings"
            )
    
    def _fetch_asset_content(self, asset: Dict[str, Any]) -> str:
        """
        Fetch content for an asset.
        
        For now, assumes content is directly in asset or fetched from URL.
        In production, this would:
        - Download from S3 if source_url provided
        - Extract text from PDFs
        - Handle various content types
        """
        # Simplified: assume we have direct text or URL
        if "content" in asset:
            return asset["content"]
        
        # For demo: generate placeholder content based on asset title
        title = asset.get("title", "Untitled")
        asset_type = asset.get("asset_type", "article")
        
        # In real implementation, fetch from source_url
        return f"{title}\n\nThis is {asset_type} content for {title}. " * 10
    
    def _store_chunks(
        self,
        db: Session,
        course_id: UUID,
        asset_id: UUID,
        chunks: List[TextChunk]
    ) -> List[UUID]:
        """Store chunks in database."""
        chunk_ids = []
        
        for chunk in chunks:
            db_chunk = ContentChunk(
                course_id=course_id,
                asset_id=asset_id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.text,
                char_count=chunk.char_count,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset
            )
            db.add(db_chunk)
            db.flush()  # Get ID without committing
            chunk_ids.append(db_chunk.id)
        
        logger.info(f"Stored {len(chunk_ids)} chunks for asset {asset_id}")
        return chunk_ids
    
    def _generate_and_store_embeddings(
        self,
        db: Session,
        course_id: UUID,
        chunk_ids: List[UUID],
        chunks: List[TextChunk]
    ) -> int:
        """Generate embeddings and store them."""
        # Get chunk texts
        chunk_texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings in batch
        embeddings = self.embedding_service.create_embeddings_batch(chunk_texts)
        
        if len(embeddings) != len(chunk_ids):
            logger.error(
                f"Embedding count mismatch: {len(embeddings)} != {len(chunk_ids)}"
            )
            return 0
        
        # Store embeddings
        for chunk_id, embedding in zip(chunk_ids, embeddings):
            db_embedding = ChunkEmbedding(
                chunk_id=chunk_id,
                course_id=course_id,
                embedding=embedding,
                model_name=settings.OPENAI_EMBEDDING_MODEL
            )
            db.add(db_embedding)
        
        logger.info(f"Stored {len(embeddings)} embeddings")
        return len(embeddings)


def run_consumer():
    """Run the Kafka consumer loop."""
    logger.info(
        f"Starting course.published consumer, "
        f"topic={settings.KAFKA_COURSE_TOPIC}, "
        f"group={settings.KAFKA_GROUP_ID}"
    )
    
    consumer = KafkaConsumer(
        settings.KAFKA_COURSE_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_GROUP_ID,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        enable_auto_commit=True
    )
    
    processor = CoursePublishedConsumer()
    
    try:
        for message in consumer:
            event = message.value
            event_type = event.get("event_type")
            
            if event_type == "course.published":
                logger.info(f"Received course.published event: {event.get('aggregate_id')}")
                processor.process_event(event)
            else:
                logger.debug(f"Ignoring event type: {event_type}")
                
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    finally:
        consumer.close()
        logger.info("Consumer closed")


if __name__ == "__main__":
    run_consumer()
