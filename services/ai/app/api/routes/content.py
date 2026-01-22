"""Content and processing API routes for AI service."""

import time
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
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
    SearchResponse,
    SearchResult
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


def _fallback_text_search(search_request: SearchRequest, db: Session):
    """Fallback text search when embeddings are not available."""
    start_time = time.time()  # Add start_time here
    logger = get_logger(__name__)
    
    query = db.query(ContentChunk)
    if search_request.course_ids:
        query = query.filter(ContentChunk.course_id.in_(search_request.course_ids))
    
    # Extract keywords from query for better text search
    import re
    query_text = search_request.query.lower()
    # Remove common words and extract meaningful terms
    keywords = re.findall(r'\b[a-zA-Z]{3,}\b', query_text)
    keywords = [k for k in keywords if k not in ['what', 'how', 'the', 'and', 'are', 'this', 'that', 'with']]
    
    logger.info(f"Text search query: '{search_request.query}' -> Keywords: {keywords}")
    
    if not keywords:
        keywords = [query_text.strip()]
    
    # Search for any of the keywords
    from sqlalchemy import or_
    search_conditions = []
    for keyword in keywords:
        search_conditions.append(ContentChunk.content.ilike(f"%{keyword}%"))
    
    if search_conditions:
        chunks = (
            query.filter(or_(*search_conditions))
            .limit(search_request.limit)
            .all()
        )
        logger.info(f"Found {len(chunks)} chunks matching keywords: {keywords}")
    else:
        chunks = []
        logger.warning(f"No search conditions generated for query: {search_request.query}")
    
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
    
    end_time = time.time()
    search_time_ms = (end_time - start_time) * 1000
    
    return SearchResponse(
        query=search_request.query,
        results=results,
        total_results=len(results),
        search_time_ms=search_time_ms
    )


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    search_request: SearchRequest,
    db: Session = Depends(get_db)
):
    """Perform semantic search across content chunks using RAG."""
    from app.services.embedding_service import get_embedding_service
    
    start_time = time.time()
    logger = get_logger(__name__)
    
    # Use unified embedding service for semantic search
    embedding_service = get_embedding_service()
    
    try:
        # Generate query embedding using configured provider
        query_embedding = embedding_service.encode_query(search_request.query)
        query_vector = query_embedding.tolist()
        
        # Build the query with course filter if needed
        course_filter = ""
        if search_request.course_ids:
            course_ids_str = "', '".join(str(cid) for cid in search_request.course_ids)
            course_filter = f"AND cc.course_id IN ('{course_ids_str}')"
        
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
            WHERE ce.model_name = :model_name
            {course_filter}
            AND (1 - (ce.embedding <=> :query_embedding)) >= :threshold
            ORDER BY ce.embedding <=> :query_embedding
            LIMIT :limit
        """)
        
        # Execute the similarity search
        result = db.execute(similarity_query, {
            "query_embedding": query_vector,
            "model_name": settings.EMBEDDING_MODEL,
            "threshold": search_request.similarity_threshold,
            "limit": search_request.limit
        })
        
        rows = result.fetchall()
        logger.info(f"Embedding search ({settings.EMBEDDING_PROVIDER}) found {len(rows)} results for query: '{search_request.query}'")
        
        results = []
        for row in rows:
            result_obj = SearchResult(
                chunk_id=row.chunk_id,
                course_id=row.course_id,
                asset_id=row.asset_id,
                content=row.content,
                similarity_score=float(row.similarity),
                chunk_index=row.chunk_index
            )
            results.append(result_obj)
                
    except Exception as e:
        logger.error(f"Embedding search failed: {e}")
        logger.info("Falling back to text search")
        # Fall back to text search
        return _fallback_text_search(search_request, db)
    
    # Return results
    end_time = time.time()
    search_time_ms = (end_time - start_time) * 1000
    
    return SearchResponse(
        query=search_request.query,
        results=results,
        total_results=len(results),
        search_time_ms=search_time_ms
    )


@router.post("/generate-embeddings")
async def generate_embeddings(
    course_id: Optional[UUID] = None,
    force_regenerate: bool = Query(default=True, description="Regenerate embeddings even if they exist"),
    db: Session = Depends(get_db)
):
    """Generate embeddings for content chunks using the configured provider."""
    from app.services.embedding_service import get_embedding_service
    
    logger = get_logger(__name__)
    
    if force_regenerate:
        # Get ALL chunks for the course (ignore existing embeddings)
        chunks_query = db.query(ContentChunk)
        if course_id:
            chunks_query = chunks_query.filter(ContentChunk.course_id == course_id)
        chunks_to_process = chunks_query.all()
        
        # Delete existing embeddings
        if chunks_to_process:
            chunk_ids = [chunk.id for chunk in chunks_to_process]
            delete_query = db.query(ChunkEmbedding).filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
            deleted_count = delete_query.count()
            delete_query.delete(synchronize_session=False)
            db.commit()
            logger.info(f"Deleted {deleted_count} existing embeddings")
    else:
        # Get chunks without embeddings only
        chunks_query = (
            db.query(ContentChunk)
            .outerjoin(ChunkEmbedding, ContentChunk.id == ChunkEmbedding.chunk_id)
            .filter(ChunkEmbedding.id.is_(None))  # No embedding exists
        )
        if course_id:
            chunks_query = chunks_query.filter(ContentChunk.course_id == course_id)
        chunks_to_process = chunks_query.all()
    
    if not chunks_to_process:
        return {"message": "No chunks to process", "updated": 0}
    
    logger.info(f"Processing {len(chunks_to_process)} chunks (force_regenerate={force_regenerate})")
    
    # Initialize embedding service
    try:
        embedding_service = get_embedding_service()
        model_info = embedding_service.get_model_info()
        logger.info(f"Using {model_info['provider']} embeddings with model: {model_info['model_name']}")
    except Exception as e:
        logger.error(f"Failed to initialize sentence-transformers: {e}")
        
        # Check for common Windows PyTorch dependency issue
        if "c10.dll" in str(e) or "WinError 126" in str(e):
            detail = (
                "PyTorch dependency missing. Please install Microsoft Visual C++ Redistributable:\n"
                "1. Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe\n"
                "2. Install and restart your terminal\n"
                "3. Try again"
            )
        else:
            detail = f"Sentence-transformers initialization error: {str(e)}"
        
        raise HTTPException(status_code=500, detail=detail)
    
    updated_count = 0
    batch_size = 32
    
    try:
        # Process chunks in batches to manage memory
        for i in range(0, len(chunks_to_process), batch_size):
            batch = chunks_to_process[i:i + batch_size]
            batch_texts = [chunk.content for chunk in batch]
            
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} chunks")
            
            # Generate embeddings for the batch
            embeddings = embedding_service.encode(batch_texts)
            
            # Prepare bulk insert data
            embedding_mappings = []
            for chunk, embedding in zip(batch, embeddings):
                embedding_mappings.append({
                    'id': uuid4(),
                    'chunk_id': chunk.id,
                    'course_id': chunk.course_id,
                    'embedding': embedding.tolist(),  # Convert numpy array to list
                    'model_name': model_info['model_name']  # Add missing model_name
                })
            
            # Bulk insert embeddings for better performance
            db.bulk_insert_mappings(ChunkEmbedding, embedding_mappings)
            updated_count += len(embedding_mappings)
            
            # Commit batch
            db.commit()
            logger.info(f"Stored {len(batch)} embeddings")
        
        return {
            "message": f"Generated {updated_count} embeddings using {model_info['provider']}",
            "updated": updated_count,
            "total_chunks": len(chunks_to_process),
            "provider": model_info['provider'],
            "model": model_info['model_name'],
            "force_regenerate": force_regenerate
        }
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {str(e)}")


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