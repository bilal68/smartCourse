"""RAG service integrating semantic search with cloud LLM providers."""

from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.modules.search.service import SearchService  
from .llm_providers import get_llm_provider, LLMProvider
from app.api.schemas import SearchRequest
from app.core.logging import get_logger


class RAGService:
    """RAG service orchestrating search and cloud LLM generation."""
    
    def __init__(self, db: Session):
        self.db = db
        self.search_service = SearchService(db)
        self._llm_provider: Optional[LLMProvider] = None
    
    def set_provider(self, provider_name: str = "groq", **kwargs):
        """Set the LLM provider (groq/openai/anthropic)."""
        self._llm_provider = get_llm_provider(provider_name, **kwargs)
    
    def ask_question(
        self,
        question: str,
        course_ids: Optional[List[str]] = None,
        mode: str = "student",
        provider: str = "groq",
        model_name: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.15  # Lowered from 0.3 to capture more results
    ) -> Dict[str, Any]:
        """
        Ask a question and get an AI-generated response using cloud LLMs.
        
        Args:
            question: User's question
            course_ids: Optional list of course IDs to search within  
            mode: Response mode ('student' or 'instructor')
            provider: LLM provider ('groq', 'openai', 'anthropic')
            model_name: Optional specific model name
            limit: Max number of chunks to retrieve
            similarity_threshold: Minimum similarity for results
        """
        logger = get_logger(__name__)
        
        try:
            # Step 1: Semantic search for relevant content
            search_request = SearchRequest(
                query=question,
                course_ids=[UUID(cid) for cid in course_ids] if course_ids else None,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            search_response = self.search_service.semantic_search(search_request)
            
            if not search_response.results:
                return {
                    "question": question,
                    "answer": "I couldn't find relevant content to answer your question.",
                    "sources": [],
                    "confidence": 0.0,
                    "mode": mode,
                    "model_info": {"provider": provider, "status": "no_content"}
                }
            
            logger.info(f"Retrieved {len(search_response.results)} chunks for RAG")
            
            # Step 2: Prepare content chunks
            chunks = []
            source_info = []
            
            for result in search_response.results:
                content = result.content
                
                # Extract readable content from JSON if needed
                if content.strip().startswith('{"schema"') or content.strip().startswith('{ "schema"'):
                    try:
                        import json
                        parsed = json.loads(content)
                        doc_structure = parsed.get('doc', {})
                        if doc_structure:
                            readable_content = self._extract_text_from_doc(doc_structure)
                            if readable_content:
                                content = readable_content
                    except Exception:
                        pass  # Use original content if parsing fails
                
                chunks.append(content)
                source_info.append({
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "similarity_score": result.similarity_score,
                    "source": f"Course content chunk {len(source_info) + 1}"
                })
            
            # Step 3: Set up LLM provider
            provider_kwargs = {}
            if model_name:
                provider_kwargs["model_name"] = model_name
                
            self.set_provider(provider, **provider_kwargs)
            
            # Step 4: Process question through LLM provider
            llm_result = self._llm_provider.process_question(
                question=question,
                retrieved_chunks=chunks,
                mode=mode
            )
            
            if llm_result.get("error"):
                logger.error(f"LLM provider error: {llm_result['error']}")
                return {
                    "question": question,
                    "answer": f"Error generating response: {llm_result['error']}",
                    "sources": source_info,
                    "confidence": float(search_response.avg_similarity) if hasattr(search_response, 'avg_similarity') else 0.0,
                    "mode": mode,
                    "model_info": self._llm_provider.get_model_info(),
                    "error": llm_result["error"]
                }
            
            # Step 5: Format successful response
            return {
                "question": question,
                "answer": llm_result["response"],
                "sources": source_info,
                "confidence": float(search_response.avg_similarity) if hasattr(search_response, 'avg_similarity') else 0.0,
                "mode": mode,
                "model_info": self._llm_provider.get_model_info()
            }
            
        except Exception as e:
            logger.error(f"RAG service error: {e}")
            return {
                "question": question,
                "answer": f"Service error: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "mode": mode,
                "model_info": {"provider": provider, "error": str(e)},
                "error": str(e)
            }
    
    def ask_question_stream(
        self,
        question: str,
        course_ids: Optional[List[str]] = None,
        mode: str = "student",
        provider: str = "groq",
        model_name: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.15
    ):
        """
        Ask a question and get a streaming AI-generated response using cloud LLMs.
        
        Args:
            question: User's question
            course_ids: Optional list of course IDs to search within  
            mode: Response mode ('student' or 'instructor')
            provider: LLM provider ('groq', 'openai', 'anthropic')
            model_name: Optional specific model name
            limit: Max number of chunks to retrieve
            similarity_threshold: Minimum similarity for results
        
        Yields:
            dict: Chunks of response data
        """
        logger = get_logger(__name__)
        
        try:
            # Step 1: Semantic search for relevant content
            search_request = SearchRequest(
                query=question,
                course_ids=[UUID(cid) for cid in course_ids] if course_ids else None,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            search_response = self.search_service.semantic_search(search_request)
            
            if not search_response.results:
                yield {
                    "type": "complete",
                    "question": question,
                    "answer": "I couldn't find relevant content to answer your question.",
                    "sources": [],
                    "confidence": 0.0,
                    "mode": mode,
                    "model_info": {"provider": provider, "status": "no_content"}
                }
                return
            
            logger.info(f"Retrieved {len(search_response.results)} chunks for RAG streaming")
            
            # Step 2: Prepare content chunks
            chunks = []
            source_info = []
            
            for result in search_response.results:
                content = result.content
                
                # Extract readable content from JSON if needed
                if content.strip().startswith('{"schema"') or content.strip().startswith('{ "schema"'):
                    try:
                        import json
                        parsed = json.loads(content)
                        doc_structure = parsed.get('doc', {})
                        if doc_structure:
                            readable_content = self._extract_text_from_doc(doc_structure)
                            if readable_content:
                                content = readable_content
                    except Exception:
                        pass  # Use original content if parsing fails
                
                chunks.append(content)
                source_info.append({
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "similarity_score": result.similarity_score,
                    "source": f"Course content chunk {len(source_info) + 1}"
                })
            
            # Step 3: Set up LLM provider
            provider_kwargs = {}
            if model_name:
                provider_kwargs["model_name"] = model_name
                
            self.set_provider(provider, **provider_kwargs)
            
            # Step 4: Send initial metadata
            yield {
                "type": "start",
                "question": question,
                "sources": source_info,
                "confidence": float(search_response.avg_similarity) if hasattr(search_response, 'avg_similarity') else 0.0,
                "mode": mode,
                "model_info": self._llm_provider.get_model_info()
            }
            
            # Step 5: Stream response from LLM provider
            try:
                for chunk in self._llm_provider.process_question_stream(
                    question=question,
                    retrieved_chunks=chunks,
                    mode=mode
                ):
                    yield chunk
                    
            except Exception as stream_error:
                logger.error(f"Streaming error: {stream_error}")
                yield {
                    "type": "error",
                    "error": f"Streaming error: {str(stream_error)}",
                    "question": question,
                    "model_info": self._llm_provider.get_model_info()
                }
            
        except Exception as e:
            logger.error(f"RAG streaming service error: {e}")
            yield {
                "type": "error",
                "error": f"Service error: {str(e)}",
                "question": question,
                "model_info": {"provider": provider, "error": str(e)}
            }
    
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