"""Cloud LLM providers for RAG generation (OpenAI/Groq/Anthropic)."""

from typing import Dict, Any, List, Optional, TypedDict
from abc import ABC, abstractmethod
import os


class RAGState(TypedDict):
    """State for RAG workflow."""
    question: str
    course_ids: Optional[List[str]]
    mode: str
    retrieved_chunks: List[str]
    context: str
    response: str
    error: Optional[str]


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def process_question(
        self,
        question: str,
        retrieved_chunks: List[str],
        mode: str = "student"
    ) -> Dict[str, Any]:
        """Process a question through the provider."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        pass


class GroqProvider(LLMProvider):
    """Groq LLM provider (FREE tier available)."""
    
    def __init__(self, model_name: str = "llama-3.1-8b-instant", api_key: str = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
    
    def process_question(
        self,
        question: str,
        retrieved_chunks: List[str],
        mode: str = "student"
    ) -> Dict[str, Any]:
        """Process question using Groq."""
        try:
            import groq
            
            client = groq.Groq(api_key=self.api_key)
            
            # Prepare context
            context = self._prepare_context(retrieved_chunks)
            
            # Create appropriate prompt based on mode
            if mode == "instructor":
                system_prompt = """You are an expert instructional designer and teacher. Based on the provided course content, help instructors create better learning materials, summaries, objectives, and assessments."""
                user_prompt = f"""Course Content:
{context}

Instructor Question: {question}

Please provide helpful suggestions for instructional design, learning objectives, or content enhancement based on the content above."""
            else:
                system_prompt = """You are a helpful learning assistant for students. Answer questions based only on the provided course content. Be clear, educational, and encouraging."""
                user_prompt = f"""Course Content:
{context}

Student Question: {question}

Please provide a clear, helpful answer based on the content above. If the content doesn't fully answer the question, mention what aspects you can address."""
            
            # Make API call
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            
            return {
                "question": question,
                "mode": mode,
                "retrieved_chunks": retrieved_chunks,
                "context": context,
                "response": response.choices[0].message.content,
                "error": None
            }
            
        except Exception as e:
            return {
                "question": question,
                "mode": mode, 
                "retrieved_chunks": retrieved_chunks,
                "context": "",
                "response": "",
                "error": f"Groq API error: {str(e)}"
            }
    
    def _prepare_context(self, chunks: List[str]) -> str:
        """Prepare context from retrieved chunks."""
        if not chunks:
            return "No relevant content found."
        
        context_parts = []
        for i, chunk in enumerate(chunks[:5], 1):
            clean_chunk = chunk.strip()
            if len(clean_chunk) > 500:
                clean_chunk = clean_chunk[:500] + "..."
            context_parts.append(f"[Content {i}]\\n{clean_chunk}")
        
        return "\\n\\n".join(context_parts)
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "groq",
            "model": self.model_name,
            "type": "cloud_api"
        }


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", api_key: str = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
    
    def process_question(
        self,
        question: str,
        retrieved_chunks: List[str],
        mode: str = "student"
    ) -> Dict[str, Any]:
        """Process question using OpenAI."""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            # Prepare context  
            context = self._prepare_context(retrieved_chunks)
            
            # Create prompt based on mode
            if mode == "instructor":
                system_prompt = """You are an expert instructional designer and teacher. Based on the provided course content, help instructors create better learning materials, summaries, objectives, and assessments."""
                user_prompt = f"""Course Content:
{context}

Instructor Question: {question}

Please provide helpful suggestions for instructional design, learning objectives, or content enhancement."""
            else:
                system_prompt = """You are a helpful learning assistant for students. Answer questions based only on the provided course content. Be clear, educational, and encouraging."""
                user_prompt = f"""Course Content:
{context}

Student Question: {question}

Please provide a clear, helpful answer based on the content above."""
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            
            return {
                "question": question,
                "mode": mode,
                "retrieved_chunks": retrieved_chunks,
                "context": context,
                "response": response.choices[0].message.content,
                "error": None
            }
            
        except Exception as e:
            return {
                "question": question,
                "mode": mode,
                "retrieved_chunks": retrieved_chunks,
                "context": "",
                "response": "",
                "error": f"OpenAI API error: {str(e)}"
            }
    
    def _prepare_context(self, chunks: List[str]) -> str:
        """Prepare context from retrieved chunks."""
        if not chunks:
            return "No relevant content found."
        
        context_parts = []
        for i, chunk in enumerate(chunks[:5], 1):
            clean_chunk = chunk.strip()
            if len(clean_chunk) > 500:
                clean_chunk = clean_chunk[:500] + "..."
            context_parts.append(f"[Content {i}]\\n{clean_chunk}")
        
        return "\\n\\n".join(context_parts)
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.model_name,
            "type": "cloud_api"
        }


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, model_name: str = "claude-3-haiku-20240307", api_key: str = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    
    def process_question(
        self,
        question: str,
        retrieved_chunks: List[str],
        mode: str = "student"
    ) -> Dict[str, Any]:
        """Process question using Anthropic Claude."""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Prepare context
            context = self._prepare_context(retrieved_chunks)
            
            # Create prompt
            if mode == "instructor":
                system_prompt = """You are an expert instructional designer and teacher. Based on the provided course content, help instructors create better learning materials, summaries, objectives, and assessments."""
                user_prompt = f"""Course Content:
{context}

Instructor Question: {question}

Please provide helpful suggestions for instructional design, learning objectives, or content enhancement."""
            else:
                system_prompt = """You are a helpful learning assistant for students. Answer questions based only on the provided course content. Be clear, educational, and encouraging."""  
                user_prompt = f"""Course Content:
{context}

Student Question: {question}

Please provide a clear, helpful answer based on the content above."""
            
            response = client.messages.create(
                model=self.model_name,
                max_tokens=1024,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            
            return {
                "question": question,
                "mode": mode,
                "retrieved_chunks": retrieved_chunks,
                "context": context,
                "response": response.content[0].text,
                "error": None
            }
            
        except Exception as e:
            return {
                "question": question,
                "mode": mode,
                "retrieved_chunks": retrieved_chunks,
                "context": "",
                "response": "",
                "error": f"Anthropic API error: {str(e)}"
            }
    
    def _prepare_context(self, chunks: List[str]) -> str:
        """Prepare context from retrieved chunks."""
        if not chunks:
            return "No relevant content found."
        
        context_parts = []
        for i, chunk in enumerate(chunks[:5], 1):
            clean_chunk = chunk.strip()
            if len(clean_chunk) > 500:
                clean_chunk = clean_chunk[:500] + "..."
            context_parts.append(f"[Content {i}]\\n{clean_chunk}")
        
        return "\\n\\n".join(context_parts)
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "anthropic",
            "model": self.model_name,
            "type": "cloud_api"
        }


def get_llm_provider(provider_name: str = "groq", **kwargs) -> LLMProvider:
    """Factory function to get LLM provider."""
    if provider_name.lower() == "groq":
        return GroqProvider(**kwargs)
    elif provider_name.lower() == "openai":
        return OpenAIProvider(**kwargs)  
    elif provider_name.lower() == "anthropic":
        return AnthropicProvider(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}. Supported: groq, openai, anthropic")