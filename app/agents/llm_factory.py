"""
LLM Factory - Configurable LLM Provider

This module provides factory functions to create LLM instances based on configuration.
Supports: OpenAI and Google Gemini

Usage:
    from app.agents.llm_factory import get_llm, get_embedding_function
    
    llm = get_llm(temperature=0)
    embed_fn = get_embedding_function()
"""

from typing import Callable, List
from app.core.config import settings

# Model configurations - centralized model names
OPENAI_CHAT_MODEL = "gpt-4o-mini"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

GEMINI_CHAT_MODEL = "gemini-2.5-flash"
GEMINI_EMBEDDING_MODEL = "models/embedding-001"


def get_llm(temperature: float = 0):
    """
    Factory function to get LLM instance based on config.
    
    Args:
        temperature: Temperature for generation (0 = deterministic, 1 = creative)
        
    Returns:
        LangChain LLM instance (ChatOpenAI or ChatGoogleGenerativeAI)
        
    Raises:
        ValueError: If LLM_PROVIDER is not supported
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=OPENAI_CHAT_MODEL,
            temperature=temperature,
            openai_api_key=settings.OPENAI_API_KEY
        )
    
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=GEMINI_CHAT_MODEL,
            temperature=temperature,
            google_api_key=settings.GOOGLE_API_KEY
        )
    
    else:
        raise ValueError(
            f"Unsupported LLM provider: {settings.LLM_PROVIDER}. "
            f"Supported providers: 'openai', 'gemini'"
        )


def get_embedding_function() -> Callable[[str], List[float]]:
    """
    Factory function to get embedding function based on config.
    
    Returns:
        Function that takes text string and returns embedding vector
        
    Raises:
        ValueError: If LLM_PROVIDER is not supported
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        def embed_openai(text: str) -> List[float]:
            """Generate embedding using OpenAI (1536 dimensions)."""
            try:
                response = client.embeddings.create(
                    model=OPENAI_EMBEDDING_MODEL,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"[❌] OpenAI embedding generation failed: {e}")
                return []
        
        return embed_openai
    
    elif provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        def embed_gemini(text: str) -> List[float]:
            """Generate embedding using Gemini (768 dimensions)."""
            try:
                result = genai.embed_content(
                    model=GEMINI_EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_document"
                )
                return result['embedding']
            except Exception as e:
                print(f"[❌] Gemini embedding generation failed: {e}")
                return []
        
        return embed_gemini
    
    else:
        raise ValueError(
            f"Unsupported LLM provider: {settings.LLM_PROVIDER}. "
            f"Supported providers: 'openai', 'gemini'"
        )


def get_llm_for_summary(temperature: float = 0):
    """
    Get LLM specifically for summary generation.
    
    This is a separate function in case we want different models
    for summarization vs. agent conversations in the future.
    
    Args:
        temperature: Temperature for generation
        
    Returns:
        LLM instance or native client based on provider
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai":
        # Return native OpenAI client for more control
        from openai import OpenAI
        return OpenAI(api_key=settings.OPENAI_API_KEY)
    
    elif provider == "gemini":
        # Return configured Gemini client
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        return genai.GenerativeModel(GEMINI_CHAT_MODEL)
    
    else:
        raise ValueError(
            f"Unsupported LLM provider: {settings.LLM_PROVIDER}. "
            f"Supported providers: 'openai', 'gemini'"
        )


__all__ = [
    "get_llm",
    "get_embedding_function",
    "get_llm_for_summary"
]
