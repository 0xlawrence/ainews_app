"""
Retry and fallback handling for LLM operations.

This module handles retry logic, fallback strategies, and error recovery
for various LLM operations with exponential backoff and graceful degradation.
"""

import asyncio
import logging
import time
from typing import List, Union, Optional, Callable, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from src.models.schemas import SummaryOutput
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class RetryHandler:
    """Handler for retry logic and fallback strategies in LLM operations."""
    
    def __init__(self, client_factory, response_parser, cost_estimator):
        """Initialize retry handler.
        
        Args:
            client_factory: Factory for creating LLM clients
            response_parser: Parser for LLM responses
            cost_estimator: Cost estimation utility
        """
        self.settings = get_settings()
        self.client_factory = client_factory
        self.response_parser = response_parser
        self.cost_estimator = cost_estimator
        
        self.primary_models = [self.settings.llm.primary_model]
        self.fallback_models = [self.settings.llm.fallback_model, self.settings.llm.final_fallback_model]
        self.retry_delay = self.settings.llm.retry_delay
        self.timeout = self.settings.llm.timeout
        
        logger.info("Retry Handler initialized with primary models: %s, fallback models: %s",
                   self.primary_models, self.fallback_models)
    
    async def ainvoke_with_retry(self, client: BaseChatModel, messages, model_name: str):
        """Wrapper around `client.ainvoke` to standardise error handling.

        Some LangChain chat model clients return a ChatMessage; others return
        a wrapper object. We keep the result as-is so that callers can access
        `.content` safely. Any networking or API error will be propagated to
        the caller and handled by the retry logic upstream.
        """
        try:
            response = await client.ainvoke(messages)
            return response
        except Exception as e:
            logger.warning("ainvoke failed (model=%s): %s", model_name, e)
            raise
    
    async def execute_with_fallback(
        self,
        operation_func: Callable,
        operation_args: dict,
        max_retries: int = 3,
        operation_name: str = "LLM_operation"
    ) -> Any:
        """
        Execute an LLM operation with retry and fallback logic.
        
        Args:
            operation_func: The operation function to execute
            operation_args: Arguments for the operation
            max_retries: Maximum retries for primary model
            operation_name: Name of the operation for logging
            
        Returns:
            Operation result or fallback result
        """
        last_error: Optional[Exception] = None
        primary_model = self.primary_models[0]
        fallback_models = self.fallback_models
        
        logger.info(
            "Attempting %s with model: %s",
            operation_name,
            primary_model
        )
        
        # Try primary model with retries
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                result = await operation_func(primary_model, **operation_args)
                
                if result:
                    processing_time = time.time() - start_time
                    logger.info(
                        "Primary model %s successful - model: %s, attempt: %d, time: %.2fs",
                        operation_name, primary_model, attempt + 1, processing_time
                    )
                    return result
                    
            except Exception as e:
                last_error = e
                processing_time = time.time() - start_time
                
                logger.warning(
                    "%s attempt failed - model: %s, attempt: %d, error: %s (%s), time: %.2fs",
                    operation_name,
                    primary_model,
                    attempt + 1,
                    str(e),
                    type(e).__name__,
                    processing_time
                )
                
                # Wait before retry with exponential backoff
                if attempt < max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        # Try fallback models (1 attempt each)
        for fallback_model in fallback_models:
            try:
                result = await operation_func(fallback_model, **operation_args)
                if result:
                    logger.info(
                        "Fallback model %s successful - model: %s",
                        operation_name, fallback_model
                    )
                    return result
                    
            except Exception as e:
                last_error = e
                logger.warning(
                    "Fallback %s failed - model: %s, error: %s",
                    operation_name, fallback_model, str(e)
                )
        
        # All models failed
        logger.error(
            "All LLM models failed for %s - last_error: %s",
            operation_name, str(last_error)
        )
        
        # Return fallback result if available
        return await self._create_operation_fallback(operation_name, operation_args, str(last_error))
    
    async def try_single_model(
        self,
        model_name: str,
        article_title: str,
        article_content: str,
        article_url: str,
        source_name: str,
        system_prompt: str,
        user_prompt: str
    ) -> Union[SummaryOutput, None]:
        """Try generating summary with a single model (helper method to reduce duplication)."""
        start_time = time.time()

        logger.info(
            "Attempting summary generation - model: %s, article: %s",
            model_name, article_title[:50] + "..."
        )

        try:
            # Get client
            client = self.client_factory.get_client(model_name)

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", user_prompt),
            ])

            formatted_prompt = prompt.format_messages()
            response = await self.ainvoke_with_retry(client, formatted_prompt, model_name)

            # Parse response using existing extraction methods
            summary = self.response_parser.extract_summary_from_response(response.content, model_name)
            if not summary:
                return None

            # Validate summary
            self.response_parser.validate_summary(summary)

            # Add metadata
            summary.model_used = model_name
            processing_time = time.time() - start_time
            estimated_cost = self.cost_estimator.estimate_cost(
                model_name, user_prompt, response.content
            )

            logger.info(
                "Summary generation successful - model: %s, time: %.2fs, cost: $%.4f, confidence: %.2f",
                model_name, processing_time, estimated_cost, summary.confidence_score
            )

            return summary
            
        except Exception as e:
            logger.warning(f"Single model attempt failed for {model_name}: {e}")
            raise
    
    def create_fallback_summary(self, article_title: str, article_content: str, last_error: str) -> SummaryOutput:
        """Create a minimal but valid SummaryOutput when all LLMs fail.

        Parameters
        ----------
        article_title : str
            Title of the article (used as first bullet point)
        article_content : str
            Raw article text – first 100 characters will be truncated.
        last_error : str
            The last error that occurred
        """
        truncated = (article_content[:100] + "...") if article_content else "内容取得に失敗しました。"
        bullets = [
            f"【速報】{article_title}",
            truncated,
            f"※自動要約に失敗したため、元記事をご確認ください。エラー: {last_error}"
        ]
        return SummaryOutput(
            summary_points=bullets,
            confidence_score=0.0,
            source_reliability="low",
            model_used="fallback",
            fallback_used=True,
            total_tokens=0,
            processing_time_seconds=0.1
        )
    
    async def _create_operation_fallback(self, operation_name: str, operation_args: dict, error: str) -> Any:
        """Create appropriate fallback result based on operation type."""
        if "summary" in operation_name.lower():
            return self.create_fallback_summary(
                operation_args.get("article_title", "Unknown Article"),
                operation_args.get("article_content", ""),
                error
            )
        elif "title" in operation_name.lower():
            return f"【AI NEWS】{operation_args.get('article_title', 'No Title')[:50]}"
        else:
            # Generic fallback
            return f"Operation {operation_name} failed: {error}"
    
    def update_retry_settings(self, retry_delay: float = None, max_retries: int = None):
        """Update retry settings dynamically."""
        if retry_delay is not None:
            self.retry_delay = retry_delay
            logger.info(f"Updated retry delay to {retry_delay}s")
        
        if max_retries is not None:
            self.max_retries = max_retries  
            logger.info(f"Updated max retries to {max_retries}")
    
    def get_retry_stats(self) -> dict:
        """Get current retry configuration statistics."""
        return {
            "primary_models": self.primary_models,
            "fallback_models": self.fallback_models,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout,
            "cached_clients": len(self.client_factory.get_cached_clients())
        }