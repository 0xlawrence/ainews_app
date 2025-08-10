"""
Consolidated error handling patterns for newsletter generation system.

This module provides standardized error handling patterns to reduce code duplication
and ensure consistent error logging and recovery across all modules.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from src.utils.error_handler import with_retry, with_fallback, _error_manager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorHandlingPatterns:
    """Standardized error handling patterns for common operations."""

    @staticmethod
    def llm_with_fallback(
        operation_name: str,
        fallback_result: Any = None,
        log_level: str = "warning"
    ):
        """
        Standard pattern for LLM operations with fallback.
        
        Args:
            operation_name: Name of the operation for logging
            fallback_result: Result to return on failure
            log_level: Logging level for failures
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    result = await func(*args, **kwargs)
                    if result is None and fallback_result is not None:
                        getattr(logger, log_level)(
                            f"{operation_name} returned empty result, using fallback"
                        )
                        return fallback_result
                    return result
                except Exception as e:
                    getattr(logger, log_level)(
                        f"{operation_name} failed, using fallback: {e}"
                    )
                    _error_manager.record_error(operation_name, e)
                    return fallback_result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                    if result is None and fallback_result is not None:
                        getattr(logger, log_level)(
                            f"{operation_name} returned empty result, using fallback"
                        )
                        return fallback_result
                    return result
                except Exception as e:
                    getattr(logger, log_level)(
                        f"{operation_name} failed, using fallback: {e}"
                    )
                    _error_manager.record_error(operation_name, e)
                    return fallback_result
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator

    @staticmethod
    def safe_initialization(
        component_name: str,
        log_level: str = "warning"
    ):
        """
        Standard pattern for safe component initialization.
        
        Args:
            component_name: Name of the component for logging
            log_level: Logging level for failures
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    getattr(logger, log_level)(
                        f"Failed to initialize {component_name}: {e}"
                    )
                    _error_manager.record_error(f"init_{component_name}", e)
                    return None
            
            return wrapper
        
        return decorator

    @staticmethod
    def process_items_safely(
        operation_name: str,
        continue_on_error: bool = True,
        log_level: str = "warning"
    ):
        """
        Standard pattern for processing collections with individual error handling.
        
        Args:
            operation_name: Name of the operation for logging
            continue_on_error: Whether to continue processing other items on error
            log_level: Logging level for individual failures
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(items: List[Any], *args, **kwargs):
                results = []
                successful_count = 0
                failed_count = 0
                
                for i, item in enumerate(items):
                    try:
                        result = await func(item, *args, **kwargs)
                        if result is not None:
                            results.append(result)
                            successful_count += 1
                    except Exception as e:
                        failed_count += 1
                        item_id = getattr(item, 'id', f'item_{i}')
                        getattr(logger, log_level)(
                            f"{operation_name} failed for {item_id}: {e}"
                        )
                        _error_manager.record_error(f"{operation_name}_item", e)
                        
                        if not continue_on_error:
                            raise
                
                if failed_count > 0:
                    logger.info(
                        f"{operation_name} completed: {successful_count} successful, "
                        f"{failed_count} failed"
                    )
                
                return results
            
            @wraps(func)
            def sync_wrapper(items: List[Any], *args, **kwargs):
                results = []
                successful_count = 0
                failed_count = 0
                
                for i, item in enumerate(items):
                    try:
                        result = func(item, *args, **kwargs)
                        if result is not None:
                            results.append(result)
                            successful_count += 1
                    except Exception as e:
                        failed_count += 1
                        item_id = getattr(item, 'id', f'item_{i}')
                        getattr(logger, log_level)(
                            f"{operation_name} failed for {item_id}: {e}"
                        )
                        _error_manager.record_error(f"{operation_name}_item", e)
                        
                        if not continue_on_error:
                            raise
                
                if failed_count > 0:
                    logger.info(
                        f"{operation_name} completed: {successful_count} successful, "
                        f"{failed_count} failed"
                    )
                
                return results
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator

    @staticmethod
    def safe_operation(
        operation_name: str,
        log_level: str = "error",
        reraise: bool = True,
        return_on_error: Any = None
    ):
        """
        Standard pattern for safe operation execution with logging.
        
        Args:
            operation_name: Name of the operation for logging
            log_level: Logging level for failures
            reraise: Whether to reraise the exception
            return_on_error: Value to return on error if not reraising
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    getattr(logger, log_level)(
                        f"{operation_name} failed: {e}"
                    )
                    _error_manager.record_error(operation_name, e)
                    
                    if reraise:
                        raise
                    return return_on_error
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    getattr(logger, log_level)(
                        f"{operation_name} failed: {e}"
                    )
                    _error_manager.record_error(operation_name, e)
                    
                    if reraise:
                        raise
                    return return_on_error
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator


class BulkErrorHandler:
    """Handler for bulk operations with error aggregation."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.successful_items = []
        self.failed_items = []
        self.errors = []
    
    def process_item(self, item: Any, processor: Callable[[Any], Any]) -> bool:
        """
        Process a single item with error handling.
        
        Args:
            item: Item to process
            processor: Function to process the item
            
        Returns:
            True if successful, False if failed
        """
        try:
            result = processor(item)
            self.successful_items.append((item, result))
            return True
        except Exception as e:
            self.failed_items.append(item)
            self.errors.append(e)
            item_id = getattr(item, 'id', str(item)[:50])
            logger.warning(
                f"{self.operation_name} failed for {item_id}: {e}"
            )
            _error_manager.record_error(f"{self.operation_name}_bulk", e)
            return False
    
    async def process_item_async(self, item: Any, processor: Callable[[Any], Any]) -> bool:
        """
        Process a single item asynchronously with error handling.
        
        Args:
            item: Item to process
            processor: Async function to process the item
            
        Returns:
            True if successful, False if failed
        """
        try:
            result = await processor(item)
            self.successful_items.append((item, result))
            return True
        except Exception as e:
            self.failed_items.append(item)
            self.errors.append(e)
            item_id = getattr(item, 'id', str(item)[:50])
            logger.warning(
                f"{self.operation_name} failed for {item_id}: {e}"
            )
            _error_manager.record_error(f"{self.operation_name}_bulk", e)
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary."""
        return {
            "operation": self.operation_name,
            "total_items": len(self.successful_items) + len(self.failed_items),
            "successful": len(self.successful_items),
            "failed": len(self.failed_items),
            "success_rate": len(self.successful_items) / max(1, len(self.successful_items) + len(self.failed_items)),
            "error_types": list(set(type(e).__name__ for e in self.errors))
        }
    
    def log_summary(self):
        """Log processing summary."""
        summary = self.get_summary()
        if summary["failed"] > 0:
            logger.info(
                f"{self.operation_name} bulk processing completed: "
                f"{summary['successful']}/{summary['total_items']} successful "
                f"({summary['success_rate']:.1%} success rate)"
            )
        else:
            logger.info(
                f"{self.operation_name} bulk processing completed successfully: "
                f"{summary['successful']} items processed"
            )


def handle_optional_dependency_error(
    dependency_name: str,
    fallback_value: Any = None,
    log_level: str = "warning"
):
    """
    Handle missing optional dependencies gracefully.
    
    Args:
        dependency_name: Name of the dependency
        fallback_value: Value to return when dependency is missing
        log_level: Logging level for the message
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ImportError as e:
                getattr(logger, log_level)(
                    f"Optional dependency {dependency_name} not available: {e}"
                )
                return fallback_value
            except Exception as e:
                if "dependencies" in str(e).lower() or "import" in str(e).lower():
                    getattr(logger, log_level)(
                        f"Dependency issue with {dependency_name}: {e}"
                    )
                    return fallback_value
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ImportError as e:
                getattr(logger, log_level)(
                    f"Optional dependency {dependency_name} not available: {e}"
                )
                return fallback_value
            except Exception as e:
                if "dependencies" in str(e).lower() or "import" in str(e).lower():
                    getattr(logger, log_level)(
                        f"Dependency issue with {dependency_name}: {e}"
                    )
                    return fallback_value
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def standardize_error_context(
    operation: str,
    module: str,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create standardized error context for consistent logging.
    
    Args:
        operation: Operation being performed
        module: Module where the operation is happening
        additional_context: Additional context information
        
    Returns:
        Standardized context dictionary
    """
    context = {
        "operation": operation,
        "module": module,
        "timestamp": logger.handlers[0].formatter.formatTime(
            logging.LogRecord("", 0, "", 0, "", (), None)
        ) if logger.handlers else None
    }
    
    if additional_context:
        context.update(additional_context)
    
    return context


# Convenience functions for common patterns

def safe_llm_call(
    operation_name: str,
    fallback_result: Any = None
):
    """Convenience function for LLM operations with fallback."""
    return ErrorHandlingPatterns.llm_with_fallback(operation_name, fallback_result)


def safe_init(component_name: str):
    """Convenience function for safe initialization."""
    return ErrorHandlingPatterns.safe_initialization(component_name)


def safe_processing(operation_name: str, continue_on_error: bool = True):
    """Convenience function for safe item processing."""
    return ErrorHandlingPatterns.process_items_safely(operation_name, continue_on_error)


def safe_operation(operation_name: str, reraise: bool = True, return_on_error: Any = None):
    """Convenience function for safe operations."""
    return ErrorHandlingPatterns.safe_operation(operation_name, reraise=reraise, return_on_error=return_on_error)


# Common error handling helpers

def log_exception_with_context(
    logger_instance: logging.Logger,
    operation: str,
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error"
):
    """
    Log exception with standardized context.
    
    Args:
        logger_instance: Logger to use
        operation: Operation that failed
        exception: Exception that occurred
        context: Additional context
        level: Logging level
    """
    error_context = {
        "operation": operation,
        "error_type": type(exception).__name__,
        "error_message": str(exception)
    }
    
    if context:
        error_context.update(context)
    
    getattr(logger_instance, level)(
        f"Operation '{operation}' failed: {exception}",
        extra=error_context
    )
    
    # Record in global error manager
    _error_manager.record_error(operation, exception, error_context)


def create_error_summary(
    operation: str,
    total_items: int,
    successful_items: int,
    failed_items: int,
    errors: List[Exception]
) -> Dict[str, Any]:
    """
    Create standardized error summary.
    
    Args:
        operation: Operation name
        total_items: Total number of items processed
        successful_items: Number of successful items
        failed_items: Number of failed items
        errors: List of errors encountered
        
    Returns:
        Error summary dictionary
    """
    return {
        "operation": operation,
        "total_items": total_items,
        "successful_items": successful_items,
        "failed_items": failed_items,
        "success_rate": successful_items / max(1, total_items),
        "error_types": list(set(type(e).__name__ for e in errors)),
        "sample_errors": [str(e) for e in errors[:3]]  # First 3 errors as samples
    }