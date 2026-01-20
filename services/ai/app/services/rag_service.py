"""RAG service for question answering using retrieved context."""
from typing import List, Dict, Any
from uuid import UUID

import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.orm import Session

from app.services.retrieval_service import get_retrieval_service, RetrievalResult
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RAGService:
    """
    Retrieval-Augmented Generation service.
    
    Combines semantic search with LLM generation.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.retrieval_service = get_retrieval_service(db)
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.chat_model = settings.OPENAI_CHAT_MODEL
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def ask(
        self,
        course_id: UUID,
        question: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Answer question using RAG.
        
        Args:
            course_id: Course to search within
            question: User's question
            top_k: Number of chunks to retrieve
            
        Returns:
            Dict with 'answer' and 'sources'
        """
        # Step 1: Retrieve relevant chunks
        logger.info(f"RAG query for course {course_id}: '{question[:50]}...'")
        chunks = self.retrieval_service.search(course_id, question, top_k)
        
        if not chunks:
            return {
                "answer": "I don't have any course content to answer this question.",
                "sources": []
            }
        
        # Step 2: Build prompt with context
        context_text = self._build_context(chunks)
        prompt = self._build_prompt(question, context_text)
        
        # Step 3: Generate answer using LLM
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful course assistant. "
                            "Answer questions ONLY using the provided course content. "
                            "If the answer is not in the provided context, say "
                            "'I don't know based on the course content.'"
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            
            logger.info(f"Generated answer: {len(answer)} chars")
            
            return {
                "answer": answer,
                "sources": [
                    {
                        "chunk_id": str(chunk.chunk_id),
                        "asset_id": str(chunk.asset_id),
                        "score": chunk.score
                    }
                    for chunk in chunks
                ]
            }
            
        except openai.OpenAIError as e:
            logger.error(f"OpenAI chat completion failed: {e}")
            raise
    
    def _build_context(self, chunks: List[RetrievalResult]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Context {i}]\n{chunk.text}\n")
        return "\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build final prompt for LLM."""
        return f"""Based on the following course content, answer the question.

Course Content:
{context}

Question: {question}

Answer:"""


def get_rag_service(db: Session) -> RAGService:
    """Factory function for dependency injection."""
    return RAGService(db)
