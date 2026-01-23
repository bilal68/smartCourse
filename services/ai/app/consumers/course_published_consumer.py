"""
Kafka consumer for course.published events.

Ingests course content, creates chunks, generates embeddings, stores in DB,
then publishes completion/failure event.
"""
import json
from typing import Dict, Any, List
from uuid import UUID, uuid4

from confluent_kafka import Consumer, KafkaError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.content.models import ContentChunk, ChunkEmbedding
from app.services.chunking_service import get_chunking_service, TextChunk
from app.services.embedding_service import get_embedding_service
from app.integrations.kafka.producer import publish_course_completion, publish_course_failure
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
                    
                    # Generate and store embeddings (graceful failure)
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
                content=chunk.text,  # Use content field instead of chunk_text
                char_count=chunk.char_count,
                start_char=chunk.start_offset,  # Map to start_char
                end_char=chunk.end_offset       # Map to end_char
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
        """Generate embeddings and store them using the configured provider."""
        if not chunk_ids or not chunks or len(chunk_ids) != len(chunks):
            logger.warning("Mismatch between chunk_ids and chunks")
            return 0
            
        logger.info(f"Creating embeddings using {settings.EMBEDDING_PROVIDER} provider with model: {settings.EMBEDDING_MODEL}")
        
        stored_count = 0
        batch_size = 32  # Process in batches to manage memory
        
        try:
            # Process chunks in batches
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_chunk_ids = chunk_ids[i:i + batch_size]
                batch_texts = [chunk.text for chunk in batch_chunks]
                
                logger.info(f"Processing embedding batch {i//batch_size + 1}: {len(batch_chunks)} chunks")
                
                # Generate embeddings using the unified service
                embeddings = self.embedding_service.encode(batch_texts)
                
                if len(embeddings) != len(batch_chunk_ids):
                    logger.error(f"Embedding count mismatch: {len(embeddings)} != {len(batch_chunk_ids)}")
                    continue
                
                # Prepare bulk insert data
                embedding_mappings = []
                for chunk_id, embedding in zip(batch_chunk_ids, embeddings):
                    embedding_mappings.append({
                        'id': uuid4(),
                        'chunk_id': chunk_id,
                        'course_id': course_id,
                        'embedding': embedding.tolist(),  # Convert numpy array to list
                        'model_name': self.embedding_service.get_model_info()['model_name']  # Add missing model_name
                    })
                
                # Bulk insert embeddings for better performance
                db.bulk_insert_mappings(ChunkEmbedding, embedding_mappings)
                stored_count += len(embedding_mappings)
                
                # Commit batch
                db.commit()
                logger.info(f"Stored {len(batch_chunks)} embeddings")
            
            logger.info(f"Successfully stored {stored_count} embeddings for course {course_id}")
            return stored_count
            
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            db.rollback()
            return 0


def run_consumer():
    """Run the Kafka consumer loop."""
    logger.info(
        f"Starting course.published consumer, "
        f"topic={settings.KAFKA_COURSE_TOPIC}, "
        f"group={settings.KAFKA_GROUP_ID}"
    )
    
    # Configure confluent-kafka consumer
    config = {
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': settings.KAFKA_GROUP_ID,
        'auto.offset.reset': 'latest',
        'enable.auto.commit': True,
        'session.timeout.ms': 30000,
        'max.poll.interval.ms': 300000
    }
    
    consumer = Consumer(config)
    consumer.subscribe([settings.KAFKA_COURSE_TOPIC])
    
    processor = CoursePublishedConsumer()
    
    try:
        while True:
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
                
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug(f"End of partition reached {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
                else:
                    logger.error(f"Kafka error: {msg.error()}")
                continue
            
            try:
                # Parse message
                event = json.loads(msg.value().decode('utf-8'))
                event_type = event.get("event_type")
                
                if event_type == "course.published":
                    logger.info(f"Received course.published event: {event.get('aggregate_id')}")
                    processor.process_event(event)
                else:
                    logger.debug(f"Ignoring event type: {event_type}")
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    finally:
        consumer.close()
        logger.info("Consumer closed")


if __name__ == "__main__":
    run_consumer()
