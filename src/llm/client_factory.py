"""
LLM client factory for creating and managing various LLM providers.

This module handles the creation and configuration of different LLM clients
including Gemini, Claude, and OpenAI with appropriate settings and validation.
"""

import logging
from typing import Any, Dict

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """Factory for creating and managing LLM clients."""
    
    def __init__(self):
        """Initialize the client factory."""
        self.settings = get_settings()
        self._clients: Dict[str, Any] = {}
        logger.info("LLM Client Factory initialized")
    
    def _create_gemini_client(self) -> Any:
        """Create Gemini client with optimized settings."""
        api_key = self.settings.llm.gemini_api_key
        
        # Debug logging for API key
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set")
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        # Validate API key format
        if not api_key.startswith("AIzaSy") or len(api_key) < 30:
            logger.warning("GEMINI_API_KEY format looks unusual (should start with 'AIzaSy' and be ~40 chars)")
        
        try:
            # Lazy import to avoid hard dependency during test collection
            from langchain_google_genai import ChatGoogleGenerativeAI

            client = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                google_api_key=api_key,
                temperature=0.3,
                max_tokens=1000,
                timeout=self.settings.llm.timeout,
                max_retries=0,  # We handle retries ourselves
            )
            logger.info("Gemini client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to create Gemini client: {e}")
            raise
    
    def _create_claude_client(self) -> Any:
        """Create Claude client with optimized settings."""
        api_key = self.settings.llm.claude_api_key
        
        if not api_key:
            logger.error("CLAUDE_API_KEY environment variable is not set")
            raise ValueError("CLAUDE_API_KEY environment variable is required")
        
        # Validate API key format
        if not api_key.startswith("sk-ant-") or len(api_key) < 50:
            logger.warning("CLAUDE_API_KEY format looks unusual (should start with 'sk-ant-' and be ~100 chars)")
        
        try:
            # Lazy import to avoid hard dependency during test collection
            from langchain_anthropic import ChatAnthropic

            client = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                anthropic_api_key=api_key,
                temperature=0.3,
                max_tokens=1000,
                timeout=self.settings.llm.timeout,
                max_retries=0,  # We handle retries ourselves
            )
            logger.info("Claude client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to create Claude client: {e}")
            raise
    
    def _create_openai_client(self) -> Any:
        """Create OpenAI client with optimized settings."""
        api_key = self.settings.llm.openai_api_key
        
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Validate API key format
        if not api_key.startswith("sk-") or len(api_key) < 40:
            logger.warning("OPENAI_API_KEY format looks unusual (should start with 'sk-' and be ~50 chars)")
        
        try:
            # Lazy import to avoid hard dependency during test collection
            from langchain_openai import ChatOpenAI

            client = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=api_key,
                temperature=0.3,
                max_tokens=1000,
                timeout=self.settings.llm.timeout,
                max_retries=0,  # We handle retries ourselves
            )
            logger.info("OpenAI client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to create OpenAI client: {e}")
            raise
    
    def get_client(self, model_name: str) -> Any:
        """
        Get or create a client for the specified model.
        
        Args:
            model_name: Name of the model/provider ('gemini', 'claude', 'openai' or full model names)
            
        Returns:
            BaseChatModel: The LLM client instance
            
        Raises:
            ValueError: If model_name is not supported
        """
        # Extract provider name from full model name
        provider_name = self._extract_provider_name(model_name)
        
        if provider_name in self._clients:
            return self._clients[provider_name]
        
        if provider_name == "gemini":
            client = self._create_gemini_client()
        elif provider_name == "claude":
            client = self._create_claude_client()
        elif provider_name == "openai":
            client = self._create_openai_client()
        else:
            raise ValueError(f"Unsupported model: {model_name}")
        
        self._clients[provider_name] = client
        logger.info(f"Created and cached client for model: {model_name} (provider: {provider_name})")
        return client
    
    def _extract_provider_name(self, model_name: str) -> str:
        """
        Extract provider name from full model name.
        
        Args:
            model_name: Full model name (e.g., 'gemini-2.5-flash-lite', 'claude-3-5-sonnet-20241022')
            
        Returns:
            str: Provider name ('gemini', 'claude', 'openai')
        """
        model_name_lower = model_name.lower()
        
        if model_name_lower.startswith('gemini'):
            return 'gemini'
        elif model_name_lower.startswith('claude'):
            return 'claude'
        elif model_name_lower.startswith('gpt') or model_name_lower.startswith('openai'):
            return 'openai'
        else:
            # Fallback: assume it's a provider name
            return model_name_lower
    
    def clear_cache(self):
        """Clear the client cache."""
        self._clients.clear()
        logger.info("Client cache cleared")
    
    def get_cached_clients(self) -> Dict[str, Any]:
        """Get all cached clients."""
        return self._clients.copy()