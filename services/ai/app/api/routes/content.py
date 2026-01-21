"""Content and processing API routes for AI service."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.content_chunk import ContentChunk
from app.models.chunk_embedding import ChunkEmbedding
from app.models.content_chunk import ContentChunk
from app.models.processing_job import ProcessingJob
from app.models.course_analysis import CourseAnalysis
from app.api.schemas import (
    ContentChunkResponse, 
    ProcessingJobResponse, 
    CourseAnalysisResponse,
    SearchRequest,
    SearchResponse
)

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/courses/{course_id}/chunks", response_model=List[ContentChunkResponse])
async def get_course_chunks(
    course_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get content chunks for a specific course."""
    chunks = (
        db.query(ContentChunk)
        .filter(ContentChunk.course_id == course_id)
        .order_by(ContentChunk.chunk_index)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return chunks


@router.get("/assets/{asset_id}/chunks", response_model=List[ContentChunkResponse])
async def get_asset_chunks(
    asset_id: UUID,
    db: Session = Depends(get_db)
):
    """Get content chunks for a specific asset."""
    chunks = (
        db.query(ContentChunk)
        .filter(ContentChunk.asset_id == asset_id)
        .order_by(ContentChunk.chunk_index)
        .all()
    )
    return chunks


@router.get("/courses/{course_id}/processing-status", response_model=ProcessingJobResponse)
async def get_processing_status(
    course_id: UUID,
    db: Session = Depends(get_db)
):
    """Get processing status for a course."""
    job = db.query(ProcessingJob).filter(ProcessingJob.course_id == course_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return job


@router.get("/processing-jobs", response_model=List[ProcessingJobResponse])
async def get_processing_jobs(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get list of processing jobs."""
    query = db.query(ProcessingJob)
    
    if status:
        query = query.filter(ProcessingJob.status == status)
    
    jobs = (
        query.order_by(ProcessingJob.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jobs


@router.get("/courses/{course_id}/analysis", response_model=CourseAnalysisResponse)
async def get_course_analysis(
    course_id: UUID,
    db: Session = Depends(get_db)
):
    """Get AI-generated analysis for a course."""
    analysis = db.query(CourseAnalysis).filter(CourseAnalysis.course_id == course_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Course analysis not found")
    return analysis


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    search_request: SearchRequest,
    db: Session = Depends(get_db)
):
    """Perform semantic search across content chunks using RAG."""
    import time
    import openai
    from app.core.config import settings
    
    start_time = time.time()
    
    # Set OpenAI API key
    openai.api_key = settings.OPENAI_API_KEY
    
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-placeholder"):
        # Fallback to text search if no OpenAI key
        query = db.query(ContentChunk)
        if search_request.course_ids:
            query = query.filter(ContentChunk.course_id.in_(search_request.course_ids))
        
        # Extract keywords from query for better text search
        import re
        query_text = search_request.query.lower()
        # Remove common words and extract meaningful terms
        keywords = re.findall(r'\b[a-zA-Z]{3,}\b', query_text)
        keywords = [k for k in keywords if k not in ['what', 'how', 'the', 'and', 'are', 'this', 'that', 'with']]
        
        # Debug: log the keywords being searched
        logger = get_logger(__name__)
        logger.info(f"Search query: '{search_request.query}' -> Keywords: {keywords}")
        
        if not keywords:
            keywords = [query_text.strip()]
        
        # Search for any of the keywords
        search_conditions = []
        for keyword in keywords:
            search_conditions.append(ContentChunk.content.ilike(f"%{keyword}%"))
        
        if search_conditions:
            from sqlalchemy import or_
            chunks = (
                query.filter(or_(*search_conditions))
                .limit(search_request.limit)
                .all()
            )
            logger.info(f"Found {len(chunks)} chunks matching keywords: {keywords}")
        else:
            chunks = []
            logger.warning(f"No search conditions generated for query: {search_request.query}")
        
        from app.api.schemas import SearchResult
        results = []
        for chunk in chunks:
            result = SearchResult(
                chunk_id=chunk.id,
                course_id=chunk.course_id,
                asset_id=chunk.asset_id,
                content=chunk.content,
                similarity_score=0.8,  # Placeholder for text search
                chunk_index=chunk.chunk_index
            )
            results.append(result)
    else:
        # Generate query embedding
        try:
            query_embedding_response = openai.embeddings.create(
                input=search_request.query,
                model=settings.OPENAI_EMBEDDING_MODEL
            )
            query_embedding = query_embedding_response.data[0].embedding
            
            # Use pgvector for similarity search
            from sqlalchemy import text
            
            # Build the query with course filter if needed
            course_filter = ""
            if search_request.course_ids:
                course_ids_str = "', '".join(str(cid) for cid in search_request.course_ids)
                course_filter = f"AND ce.course_id IN ('{course_ids_str}')"
            
            # PostgreSQL query using pgvector cosine similarity
            similarity_query = text(f"""
                SELECT 
                    cc.id as chunk_id,
                    cc.course_id,
                    cc.asset_id,
                    cc.content,
                    cc.chunk_index,
                    (ce.embedding <=> :query_embedding) as distance,
                    (1 - (ce.embedding <=> :query_embedding)) as similarity
                FROM content_chunks cc
                JOIN chunk_embeddings ce ON cc.id = ce.chunk_id
                WHERE (1 - (ce.embedding <=> :query_embedding)) >= :threshold
                {course_filter}
                ORDER BY ce.embedding <=> :query_embedding
                LIMIT :limit
            """)
            
            # Execute the query
            result_rows = db.execute(
                similarity_query,
                {
                    "query_embedding": query_embedding,  # Pass as list, not string
                    "threshold": search_request.similarity_threshold,
                    "limit": search_request.limit
                }
            ).fetchall()
            
            # Convert to SearchResult objects
            from app.api.schemas import SearchResult
            results = []
            for row in result_rows:
                result = SearchResult(
                    chunk_id=row.chunk_id,
                    course_id=row.course_id,
                    asset_id=row.asset_id,
                    content=row.content,
                    similarity_score=float(row.similarity),
                    chunk_index=row.chunk_index
                )
                results.append(result)
            
        except Exception as e:
            # Fallback to text search on error
            logger = get_logger(__name__)
            logger.error(f"Vector search error: {e}")
            
            query = db.query(ContentChunk)
            if search_request.course_ids:
                query = query.filter(ContentChunk.course_id.in_(search_request.course_ids))
            
            chunks = (
                query.filter(ContentChunk.content.ilike(f"%{search_request.query}%"))
                .limit(search_request.limit)
                .all()
            )
            
            from app.api.schemas import SearchResult
            results = []
            for chunk in chunks:
                result = SearchResult(
                    chunk_id=chunk.id,
                    course_id=chunk.course_id,
                    asset_id=chunk.asset_id,
                    content=chunk.content,
                    similarity_score=0.8,  # Fallback score
                    chunk_index=chunk.chunk_index
                )
                results.append(result)
    
    search_time = (time.time() - start_time) * 1000
    
    return SearchResponse(
        query=search_request.query,
        results=results,
        total_results=len(results),
        search_time_ms=search_time
    )


@router.post("/generate-embeddings")
async def generate_embeddings(
    course_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Generate embeddings for content chunks that don't have them yet."""
    import openai
    from app.core.config import settings
    
    # Check if we should use dummy embeddings for testing
    use_dummy = not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-placeholder")
    
    if not use_dummy:
        openai.api_key = settings.OPENAI_API_KEY
    
    # Get chunks without embeddings (left join to check for missing embeddings)
    from sqlalchemy.orm import joinedload
    from sqlalchemy import and_, or_
    
    chunks_query = (
        db.query(ContentChunk)
        .outerjoin(ChunkEmbedding, ContentChunk.id == ChunkEmbedding.chunk_id)
        .filter(ChunkEmbedding.id.is_(None))  # No embedding exists
    )
    
    if course_id:
        chunks_query = chunks_query.filter(ContentChunk.course_id == course_id)
    
    chunks_without_embeddings = chunks_query.all()
    
    if not chunks_without_embeddings:
        return {"message": "All chunks already have embeddings", "updated": 0}
    
    logger = get_logger(__name__)
    updated_count = 0
    batch_size = settings.EMBEDDING_BATCH_SIZE
    
    if use_dummy:
        # Create dummy embeddings for testing
        import random
        logger.warning("Creating dummy embeddings for testing - not real semantic vectors!")
        
        for chunk in chunks_without_embeddings:
            # Create a dummy 1536-dimensional vector with content-based variation
            dummy_vector = [random.uniform(-0.1, 0.1) for _ in range(settings.OPENAI_EMBEDDING_DIMENSION)]
            
            # Add some content-based variation (simple hash-based)
            content_hash = hash(chunk.content) % 1000
            dummy_vector[0] = content_hash / 1000.0
            
            chunk_embedding = ChunkEmbedding(
                chunk_id=chunk.id,
                course_id=chunk.course_id,
                embedding=dummy_vector,
                model_name="dummy-testing-model"
            )
            db.add(chunk_embedding)
            updated_count += 1
        
        db.commit()
        return {
            "message": f"Created {updated_count} DUMMY embeddings for testing (NOT real semantic vectors)",
            "updated": updated_count,
            "total_chunks": len(chunks_without_embeddings),
            "warning": "These are random vectors for testing RAG architecture only"
        }
    
    # Process in batches with real OpenAI embeddings
    for i in range(0, len(chunks_without_embeddings), batch_size):
        batch = chunks_without_embeddings[i:i + batch_size]
        texts = [chunk.content for chunk in batch]
        
        try:
            # Generate embeddings for batch
            response = openai.embeddings.create(
                input=texts,
                model=settings.OPENAI_EMBEDDING_MODEL
            )
            
            # Create ChunkEmbedding records
            for j, chunk in enumerate(batch):
                embedding_vector = response.data[j].embedding
                
                # Create ChunkEmbedding record
                chunk_embedding = ChunkEmbedding(
                    chunk_id=chunk.id,
                    course_id=chunk.course_id,
                    embedding=embedding_vector,
                    model_name=settings.OPENAI_EMBEDDING_MODEL
                )
                db.add(chunk_embedding)
                updated_count += 1
            
            # Commit batch
            db.commit()
            logger.info(f"Generated embeddings for batch {i//batch_size + 1}, updated {len(batch)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings for batch {i//batch_size + 1}: {e}")
            db.rollback()
            continue
    
    return {
        "message": f"Generated {updated_count} REAL semantic embeddings",
        "updated": updated_count,
        "total_chunks": len(chunks_without_embeddings)
    }


@router.get("/courses/{course_id}/stats")
async def get_course_stats(
    course_id: UUID,
    db: Session = Depends(get_db)
):
    """Get statistics for a course's content."""
    chunk_count = db.query(ContentChunk).filter(ContentChunk.course_id == course_id).count()
    
    if chunk_count == 0:
        raise HTTPException(status_code=404, detail="No content found for course")
    
    # Get total token count
    total_tokens = (
        db.query(ContentChunk.token_count)
        .filter(ContentChunk.course_id == course_id)
        .all()
    )
    total_token_count = sum(tokens[0] for tokens in total_tokens)
    
    # Get unique asset count
    asset_count = (
        db.query(ContentChunk.asset_id)
        .filter(ContentChunk.course_id == course_id)
        .distinct()
        .count()
    )
    
    return {
        "course_id": course_id,
        "total_chunks": chunk_count,
        "total_tokens": total_token_count,
        "unique_assets": asset_count,
        "avg_tokens_per_chunk": total_token_count / chunk_count if chunk_count > 0 else 0
    }


@router.post("/chat")
async def contextual_chat(
    request: dict,  # {"question": "...", "course_ids": [...], "mode": "student" or "instructor"}
    db: Session = Depends(get_db)
):
    """
    Intelligent Learning Assistant - Full RAG with streaming responses.
    
    Supports:
    A. Contextual Q&A for Students
    B. Content Enhancement for Instructors (summaries, objectives, quiz questions)
    """
    question = request.get("question", "")
    course_ids = request.get("course_ids", [])
    mode = request.get("mode", "student")  # "student" or "instructor"
    
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    # Step 1: Retrieve relevant content chunks
    search_request = SearchRequest(
        query=question,
        course_ids=[UUID(cid) for cid in course_ids] if course_ids else None,
        limit=5,
        similarity_threshold=0.3
    )
    
    # Reuse our search logic
    search_response = await semantic_search(search_request, db)
    
    if not search_response.results:
        def no_content_response():
            yield f"I couldn't find relevant content for your question: '{question}'. "
            yield "Could you please rephrase or ask about specific course topics?"
        
        return StreamingResponse(no_content_response(), media_type="text/plain")
    
    # Step 2: Generate contextual response with streaming
    def generate_rag_response():
        import openai
        from app.core.config import settings
        
        # Check if we have OpenAI key
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-placeholder"):
            # Fallback response for testing
            yield f"**[Testing Mode - No OpenAI Key]**\\n\\n"
            yield f"**Question:** {question}\\n\\n"
            yield f"**Found {len(search_response.results)} relevant content sections:**\\n\\n"
            
            for i, result in enumerate(search_response.results, 1):
                # Extract readable content from the JSON structure
                content = result.content
                logger = get_logger(__name__)
                logger.info(f"RAW CONTENT FOR RESULT {i}: {repr(content[:300])}")
                if content.strip().startswith('{"schema"') or content.strip().startswith('{ "schema"'):
                    import json
                    logger = get_logger(__name__)
                    logger.info(f"ATTEMPTING JSON PARSE FOR RESULT {i}")
                    try:
                        parsed = json.loads(content)
                        logger.info(f"JSON PARSE SUCCESS - Keys: {parsed.keys()}")
                        
                        doc_structure = parsed.get('doc', {})
                        logger.info(f"DOC STRUCTURE - Keys: {doc_structure.keys()}")
                        
                        if doc_structure:
                            logger.info(f"CALLING extract_text_from_doc...")
                            readable_content = extract_text_from_doc(doc_structure)
                            logger.info(f"EXTRACT RESULT - Length: {len(readable_content) if readable_content else 0}")
                            logger.info(f"EXTRACT RESULT - Content: {repr(readable_content[:100]) if readable_content else 'None'}")
                            
                            if readable_content:
                                content = readable_content
                                yield f"**{i}.** {content[:300]}{'...' if len(content) > 300 else ''}\\n\\n"
                            else:
                                logger.error("EXTRACT_TEXT_FROM_DOC returned empty result")
                                yield f"**{i}.** [Text extraction failed - no readable content found]\\n\\n"
                        else:
                            logger.error("NO DOC STRUCTURE FOUND")
                            yield f"**{i}.** [No doc structure found in JSON]\\n\\n"
                    except Exception as e:
                        logger.error(f"JSON PARSING ERROR: {str(e)}")
                        yield f"**{i}.** [JSON parsing error: {str(e)}]\\n\\n"
                else:
                    # Non-JSON content
                    if len(content) > 300:
                        content = content[:300] + "..."
                    yield f"**{i}.** {content}\\n\\n"
            
            if mode == "instructor":
                yield f"**[Instructor Mode]** This would generate summaries, objectives, or quiz questions based on the content above.\\n"
            return
        
        # Prepare context from retrieved chunks
        context_chunks = []
        for result in search_response.results:
            # Parse JSON content if needed (simplified)
            content = result.content
            if content.startswith('{"schema"'):
                # Extract text from JSON structure (simplified - you may want better parsing)
                import json
                try:
                    parsed = json.loads(content)
                    # Extract text content from the doc structure
                    content = extract_text_from_doc(parsed.get('doc', {}))
                except:
                    content = result.content[:500]
            
            context_chunks.append({
                'content': content[:800],  # Limit chunk size
                'similarity': result.similarity_score
            })
        
        # Create system prompt based on mode
        if mode == "instructor":
            system_prompt = '''You are an AI assistant for course instructors. Based on the provided course content, you can:
- Generate course summaries
- Create learning objectives  
- Design quiz questions
- Suggest improvements
- Analyze content effectiveness

Provide detailed, professional responses that help instructors enhance their courses.'''
        else:
            system_prompt = '''You are an intelligent learning assistant for students. Your role is to:
- Answer questions about course content clearly and accurately
- Provide explanations that build understanding
- Reference specific course materials when relevant
- Help students connect concepts and apply knowledge
- Be encouraging and supportive in your responses

Always base your answers on the provided course content.'''
        
        # Prepare context
        context_text = "\\n\\n".join([f"Content Section {i+1} (similarity: {chunk['similarity']:.2f}):\\n{chunk['content']}" 
                                     for i, chunk in enumerate(context_chunks)])
        
        # Create messages for OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Based on the following course content, please answer this question: "{question}"

Course Content:
{context_text}

Please provide a comprehensive answer based on the course material above."""}
        ]
        
        try:
            openai.api_key = settings.OPENAI_API_KEY
            
            # Stream the response
            response = openai.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=messages,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"OpenAI chat error: {e}")
            yield f"I apologize, but I encountered an error generating a response. Here's what I found in the course content:\\n\\n"
            
            for i, result in enumerate(search_response.results, 1):
                content = result.content[:300] + "..." if len(result.content) > 300 else result.content
                yield f"**Section {i}:** {content}\\n\\n"
    
    return StreamingResponse(generate_rag_response(), media_type="text/plain")


def extract_text_from_doc(doc):
    """Extract readable text from course editor JSON structure."""
    if not doc or 'content' not in doc:
        return ""
    
    text_parts = []
    
    def extract_from_content(content_list):
        for item in content_list:
            if not isinstance(item, dict):
                continue
                
            item_type = item.get('type', '')
            
            if item_type == 'text':
                text_parts.append(item.get('text', ''))
                
            elif item_type == 'paragraph':
                if 'content' in item:
                    extract_from_content(item['content'])
                text_parts.append(' ')  # Add space after paragraph
                
            elif item_type == 'heading':
                if 'content' in item:
                    text_parts.append('\\n# ')  # Add heading marker
                    extract_from_content(item['content'])
                    text_parts.append('\\n')
                    
            elif item_type in ['orderedList', 'bulletList']:
                text_parts.append('\\n')
                if 'content' in item:
                    extract_from_content(item['content'])
                text_parts.append('\\n')
                
            elif item_type == 'listItem':
                text_parts.append('\\n• ')
                if 'content' in item:
                    extract_from_content(item['content'])
                    
            elif item_type == 'codeBlock':
                text_parts.append('\\n```\\n')
                if 'content' in item:
                    extract_from_content(item['content'])
                text_parts.append('\\n```\\n')
                
            elif 'content' in item:
                # Handle other types that have content
                extract_from_content(item['content'])
    
    try:
        extract_from_content(doc['content'])
        result = ''.join(text_parts).strip()
        # Clean up extra whitespace
        import re
        result = re.sub(r'\\n\\s*\\n\\s*\\n+', '\\n\\n', result)
        result = re.sub(r' +', ' ', result)
        return result
    except Exception as e:
        return f"Text extraction error: {str(e)}"