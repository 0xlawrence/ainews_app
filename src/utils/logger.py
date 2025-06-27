"""
Structured logging configuration for the AI News Newsletter system.

This module sets up structured logging using structlog with JSON output
for better observability and debugging.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.typing import FilteringBoundLogger


def setup_logging(
    level: str = "INFO",
    json_logs: bool = True,
    show_locals: bool = False
) -> FilteringBoundLogger:
    """
    Setup structured logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Whether to output JSON formatted logs
        show_locals: Whether to include local variables in tracebacks
    
    Returns:
        Configured structlog logger
    """
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        stream=sys.stdout,
        format="%(message)s" if json_logs else "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if show_locals:
        processors.append(structlog.processors.dict_tracebacks)
    else:
        processors.append(structlog.processors.format_exc_info)
    
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FUNC_NAME]
            ),
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()


def log_processing_stage(
    logger: FilteringBoundLogger,
    stage: str,
    processing_id: str,
    start_time: float = None,
    end_time: float = None,
    **kwargs: Any
) -> None:
    """
    Log a processing stage with consistent format.
    
    Args:
        logger: Structlog logger instance
        stage: Processing stage name
        processing_id: Unique processing ID
        start_time: Stage start timestamp
        end_time: Stage end timestamp
        **kwargs: Additional context data
    """
    
    log_data = {
        "stage": stage,
        "processing_id": processing_id,
        **kwargs
    }
    
    if start_time and end_time:
        log_data["duration_seconds"] = round(end_time - start_time, 2)
    
    logger.info("Processing stage completed", **log_data)


def log_llm_call(
    logger: FilteringBoundLogger,
    model: str,
    prompt_tokens: int = None,
    completion_tokens: int = None,
    cost_usd: float = None,
    success: bool = True,
    error: str = None,
    **kwargs: Any
) -> None:
    """
    Log LLM API call with usage statistics.
    
    Args:
        logger: Structlog logger instance
        model: LLM model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        cost_usd: Estimated cost in USD
        success: Whether the call was successful
        error: Error message if failed
        **kwargs: Additional context data
    """
    
    log_data = {
        "event_type": "llm_call",
        "model": model,
        "success": success,
        **kwargs
    }
    
    if prompt_tokens:
        log_data["prompt_tokens"] = prompt_tokens
    if completion_tokens:
        log_data["completion_tokens"] = completion_tokens
    if cost_usd:
        log_data["cost_usd"] = round(cost_usd, 4)
    if error:
        log_data["error"] = error
    
    level = "info" if success else "error"
    getattr(logger, level)("LLM call completed", **log_data)


def log_article_processing(
    logger: FilteringBoundLogger,
    article_id: str,
    stage: str,
    success: bool = True,
    error: str = None,
    metadata: Dict[str, Any] = None,
    **kwargs: Any
) -> None:
    """
    Log article processing event.
    
    Args:
        logger: Structlog logger instance
        article_id: Article identifier
        stage: Processing stage
        success: Whether processing was successful
        error: Error message if failed
        metadata: Additional article metadata
        **kwargs: Additional context data
    """
    
    log_data = {
        "event_type": "article_processing",
        "article_id": article_id,
        "stage": stage,
        "success": success,
        **kwargs
    }
    
    if metadata:
        log_data["metadata"] = metadata
    if error:
        log_data["error"] = error
    
    level = "info" if success else "error"
    getattr(logger, level)("Article processing event", **log_data)


def create_processing_context(
    processing_id: str,
    stage: str = None,
    article_id: str = None
) -> Dict[str, str]:
    """
    Create standard processing context for logging.
    
    Args:
        processing_id: Unique processing session ID
        stage: Current processing stage
        article_id: Article being processed
    
    Returns:
        Context dictionary for logging
    """
    
    context = {"processing_id": processing_id}
    
    if stage:
        context["stage"] = stage
    if article_id:
        context["article_id"] = article_id
    
    return context