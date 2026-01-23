"""Service layer for search operations."""

import time
from typing import List, Optional, Iterator
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.search.repository import SearchRepository
from app.api.schemas import SearchRequest, SearchResponse, SearchResult
from app.core.logging import get_logger
from app.core.config import settings


class SearchService:
    """Service layer for search operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.search_repo = SearchRepository(db)

    def _to_pgvector_literal(self, vec: List[float]) -> str:
        """Convert a Python list[float] into a pgvector literal string: '[0.1,0.2,...]'."""
        return "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"

    def _fallback_text_search(self, search_request: SearchRequest) -> SearchResponse:
        """Fallback text search when embeddings are not available."""
        start_time = time.time()
        logger = get_logger(__name__)
        
        chunks = self.search_repo.text_search(
            query=search_request.query,
            course_ids=search_request.course_ids,
            limit=search_request.limit
        )
        
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

    def semantic_search(self, search_request: SearchRequest) -> SearchResponse:
        """Perform semantic search across content chunks using pgvector cosine distance."""
        from app.services.embedding_service import get_embedding_service

        start_time = time.time()
        logger = get_logger(__name__)

        embedding_service = get_embedding_service()

        try:
            # 1) Create query embedding (must match stored dimension, e.g. 384)
            query_embedding = embedding_service.encode_query(search_request.query)

            # query_embedding could be numpy array; normalize to list[float]
            if hasattr(query_embedding, "tolist"):
                query_vector = query_embedding.tolist()
            else:
                query_vector = list(query_embedding)

            logger.info(f"Generated query embedding with shape: {len(query_vector)} dimensions")

            # 2) Convert to pgvector literal string
            query_embedding_str = self._to_pgvector_literal(query_vector)

            # 3) Prepare course filter
            course_ids_str = None
            if getattr(search_request, "course_ids", None):
                course_ids_str = [str(cid) for cid in search_request.course_ids]

            # 4) Perform semantic search
            rows = self.search_repo.semantic_search(
                query_embedding_str=query_embedding_str,
                model_name=settings.EMBEDDING_MODEL,
                similarity_threshold=search_request.similarity_threshold,
                limit=search_request.limit,
                course_ids=course_ids_str
            )

            logger.info(
                f"Embedding search ({settings.EMBEDDING_PROVIDER}) found {len(rows)} results for query: '{search_request.query}'"
            )

            # Debug top 3
            for i, row in enumerate(rows[:3]):
                logger.info(
                    f"Result {i+1}: similarity={float(row['similarity']):.4f}, distance={float(row['distance']):.4f}"
                )

            results: List[SearchResult] = []
            for row in rows:
                results.append(
                    SearchResult(
                        chunk_id=row["chunk_id"],
                        course_id=row["course_id"],
                        asset_id=row["asset_id"],
                        content=row["content"],
                        similarity_score=float(row["similarity"]),
                        chunk_index=row["chunk_index"],
                    )
                )

            search_time_ms = (time.time() - start_time) * 1000

            return SearchResponse(
                query=search_request.query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms,
            )

        except Exception as e:
            logger.error(f"Embedding search failed with error type: {type(e).__name__}")
            logger.error(f"Embedding search failed with message: {str(e)}")

            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            logger.info("Rolling back transaction and falling back to text search")
            self.db.rollback()
            return self._fallback_text_search(search_request)

    def contextual_chat(
        self,
        question: str,
        course_ids: Optional[List[str]] = None,
        mode: str = "student",
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> Iterator[str]:
        """
        Intelligent Learning Assistant - Full RAG with streaming responses.
        
        Supports:
        A. Contextual Q&A for Students
        B. Content Enhancement for Instructors (summaries, objectives, quiz questions)
        """
        logger = get_logger(__name__)
        
        # Step 1: Retrieve relevant content chunks
        search_request = SearchRequest(
            query=question,
            course_ids=[UUID(cid) for cid in course_ids] if course_ids else None,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        # Perform semantic search
        search_response = self.semantic_search(search_request)
        
        if not search_response.results:
            yield f"I couldn't find relevant content for your question: '{question}'. "
            yield "Could you please rephrase or ask about specific course topics?"
            return
        
        # Step 2: Generate contextual response
        yield f"**Question:** {question}\\n\\n"
        yield f"**Found {len(search_response.results)} relevant content sections:**\\n\\n"
        
        for i, result in enumerate(search_response.results, 1):
            # Extract readable content from the JSON structure
            content = result.content
            
            if content.strip().startswith('{"schema"') or content.strip().startswith('{ "schema"'):
                import json
                try:
                    parsed = json.loads(content)
                    doc_structure = parsed.get('doc', {})
                    
                    if doc_structure:
                        readable_content = self._extract_text_from_doc(doc_structure)
                        if readable_content:
                            content = readable_content
                        else:
                            content = "[Text extraction failed - no readable content found]"
                    else:
                        content = "[No doc structure found in JSON]"
                except Exception as e:
                    content = f"[JSON parsing error: {str(e)}]"
            
            # Show content with similarity score
            if len(content) > 300:
                content = content[:300] + "..."
            
            similarity_pct = int(result.similarity_score * 100) if hasattr(result, 'similarity_score') else 80
            yield f"**{i}.** (Similarity: {similarity_pct}%) {content}\\n\\n"
        
        if mode == "instructor":
            yield f"**[Instructor Mode]** Based on the content above, you can create summaries, learning objectives, or quiz questions.\\n"

    def _extract_text_from_doc(self, doc: dict) -> str:
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