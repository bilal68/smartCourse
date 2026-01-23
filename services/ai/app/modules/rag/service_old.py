"""Enhanced RAG service with proper LLM integration."""

from typing import List, Optional, Iterator
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.search.service import SearchService
from app.modules.rag.llm_providers import get_llm_provider
from app.api.schemas import SearchRequest
from app.core.logging import get_logger


class RAGService:
    """Enhanced RAG service with proper LLM integration."""
    
    def __init__(self, db: Session, llm_provider: str = "ollama"):
        self.db = db
        self.search_service = SearchService(db)
        self.llm_provider = get_llm_provider(llm_provider)
    
    def ask_question(
        self,
        question: str,
        course_ids: Optional[List[str]] = None,
        mode: str = "student",
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> Iterator[str]:
        """
        Enhanced RAG pipeline:
        1. Query processing
        2. Content retrieval  
        3. Context preparation
        4. LLM generation
        """
        logger = get_logger(__name__)
        
        # Step 1: Process the query (could add query expansion here)
        processed_query = self._process_query(question)
        
        # Step 2: Retrieve relevant content
        search_request = SearchRequest(
            query=processed_query,
            course_ids=[UUID(cid) for cid in course_ids] if course_ids else None,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        search_response = self.search_service.semantic_search(search_request)
        
        if not search_response.results:
            yield "I couldn't find relevant content to answer your question. "
            yield "Could you please rephrase or ask about specific course topics?"
            return
        
        logger.info(f"Retrieved {len(search_response.results)} relevant chunks for RAG generation")
        
        # Step 3: Prepare context from retrieved chunks
        context_chunks = self._prepare_context(search_response.results)
        
        # Step 4: Generate response using LLM
        try:
            for chunk in self.llm_provider.generate_response(
                query=question,
                context_chunks=context_chunks,
                mode=mode
            ):
                yield chunk
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback to basic search results
            yield f"**Question:** {question}\\n\\n"
            yield f"**Found {len(search_response.results)} relevant sections:**\\n\\n"
            
            for i, result in enumerate(search_response.results[:3], 1):
                content = result.content[:200] + "..." if len(result.content) > 200 else result.content
                similarity_pct = int(result.similarity_score * 100)
                yield f"**{i}.** (Similarity: {similarity_pct}%) {content}\\n\\n"
    
    def _process_query(self, query: str) -> str:
        """Process and potentially expand the query."""
        # For now, just return as-is
        # Later you could add:
        # - Query expansion
        # - Intent detection
        # - Keyword extraction
        return query.strip()
    
    def _prepare_context(self, search_results) -> List[str]:
        """Prepare context chunks for LLM."""
        context_chunks = []
        
        for result in search_results:
            content = result.content
            
            # Extract readable content from JSON if needed
            if content.strip().startswith('{"schema"') or content.strip().startswith('{ "schema"'):
                import json
                try:
                    parsed = json.loads(content)
                    doc_structure = parsed.get('doc', {})
                    
                    if doc_structure:
                        readable_content = self._extract_text_from_doc(doc_structure)
                        if readable_content:
                            content = readable_content
                except Exception:
                    pass  # Use original content if parsing fails
            
            context_chunks.append(content)
        
        return context_chunks
    
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
                    text_parts.append(' ')
                    
                elif item_type == 'heading':
                    if 'content' in item:
                        text_parts.append('\\n# ')
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
                    extract_from_content(item['content'])
        
        try:
            extract_from_content(doc['content'])
            result = ''.join(text_parts).strip()
            import re
            result = re.sub(r'\\n\\s*\\n\\s*\\n+', '\\n\\n', result)
            result = re.sub(r' +', ' ', result)
            return result
        except Exception:
            return ""