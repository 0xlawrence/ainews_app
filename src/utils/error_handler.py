"""
Enhanced error handling and recovery system.

This module provides robust error handling, retry mechanisms,
circuit breakers, and graceful degradation for reliable operation.
"""

import asyncio
import random
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any

from src.utils.logger import setup_logging

logger = setup_logging()


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecoveryStrategy(str, Enum):
    """Recovery strategies for different error types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    FAIL_FAST = "fail_fast"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    attempt: int
    max_attempts: int
    last_error: Exception | None
    start_time: datetime
    total_duration: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: list[type[Exception]] = field(default_factory=lambda: [Exception])
    stop_on: list[type[Exception]] = field(default_factory=list)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: type[Exception] = Exception


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return True

        return (
            datetime.now() - self.last_failure_time
        ).total_seconds() > self.config.recovery_timeout

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Require multiple successes
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker reset to CLOSED")
        else:
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.success_count = 0

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


class ErrorRecoveryManager:
    """Manages error recovery strategies and patterns."""

    def __init__(self):
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.error_patterns: dict[str, list[dict[str, Any]]] = {}
        self.recovery_strategies: dict[str, RecoveryStrategy] = {}

        # Default strategies for common operations
        self._setup_default_strategies()

    def _setup_default_strategies(self):
        """Setup default recovery strategies."""
        self.recovery_strategies.update({
            "llm_api_call": RecoveryStrategy.RETRY,
            "database_operation": RecoveryStrategy.RETRY,
            "file_operation": RecoveryStrategy.RETRY,
            "network_request": RecoveryStrategy.CIRCUIT_BREAKER,
            "content_validation": RecoveryStrategy.FALLBACK,
            "embedding_generation": RecoveryStrategy.RETRY
        })

    def get_circuit_breaker(self, operation: str) -> CircuitBreaker:
        """Get or create circuit breaker for operation."""
        if operation not in self.circuit_breakers:
            config = CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0
            )
            self.circuit_breakers[operation] = CircuitBreaker(config)

        return self.circuit_breakers[operation]

    def record_error(
        self,
        operation: str,
        error: Exception,
        context: dict[str, Any] = None
    ):
        """Record error for pattern analysis."""
        if operation not in self.error_patterns:
            self.error_patterns[operation] = []

        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "stack_trace": traceback.format_exc()
        }

        self.error_patterns[operation].append(error_record)

        # Keep only recent errors (last 100)
        if len(self.error_patterns[operation]) > 100:
            self.error_patterns[operation] = self.error_patterns[operation][-100:]

    def get_recommended_strategy(self, operation: str, error: Exception) -> RecoveryStrategy:
        """Get recommended recovery strategy based on patterns."""
        # Check for specific error types
        error_type = type(error).__name__

        if "timeout" in error_type.lower() or "timeout" in str(error).lower():
            return RecoveryStrategy.RETRY
        elif "rate" in str(error).lower() or "quota" in str(error).lower():
            return RecoveryStrategy.CIRCUIT_BREAKER
        elif "validation" in error_type.lower():
            return RecoveryStrategy.FALLBACK
        elif "permission" in str(error).lower() or "auth" in str(error).lower():
            return RecoveryStrategy.FAIL_FAST

        # Use operation-specific strategy
        return self.recovery_strategies.get(operation, RecoveryStrategy.RETRY)


# Global error recovery manager
_error_manager = ErrorRecoveryManager()


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: list[type[Exception]] = None,
    stop_on: list[type[Exception]] = None
):
    """Decorator for automatic retry with exponential backoff."""

    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retry_on=retry_on or [Exception],
        stop_on=stop_on or []
    )

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = ErrorContext(
                operation=func.__name__,
                attempt=0,
                max_attempts=config.max_attempts,
                last_error=None,
                start_time=datetime.now(),
                total_duration=0.0
            )

            for attempt in range(config.max_attempts):
                context.attempt = attempt + 1

                try:
                    result = await func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(
                            f"Operation {func.__name__} succeeded after {attempt + 1} attempts"
                        )

                    return result

                except Exception as e:
                    context.last_error = e
                    context.total_duration = (
                        datetime.now() - context.start_time
                    ).total_seconds()

                    # Record error for analysis
                    _error_manager.record_error(
                        func.__name__,
                        e,
                        {"attempt": attempt + 1, "args_count": len(args)}
                    )

                    # Check if we should stop retrying
                    if any(isinstance(e, exc_type) for exc_type in config.stop_on):
                        logger.error(f"Stopping retry for {func.__name__} due to: {e}")
                        raise

                    # Check if we should retry
                    if not any(isinstance(e, exc_type) for exc_type in config.retry_on):
                        logger.error(f"Not retrying {func.__name__} for: {e}")
                        raise

                    # Check if this is the last attempt
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}: {e}"
                        )
                        raise

                    # Calculate delay for next attempt
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    if config.jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds"
                    )

                    await asyncio.sleep(delay)

            # This should never be reached
            raise context.last_error

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = ErrorContext(
                operation=func.__name__,
                attempt=0,
                max_attempts=config.max_attempts,
                last_error=None,
                start_time=datetime.now(),
                total_duration=0.0
            )

            for attempt in range(config.max_attempts):
                context.attempt = attempt + 1

                try:
                    result = func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(
                            f"Operation {func.__name__} succeeded after {attempt + 1} attempts"
                        )

                    return result

                except Exception as e:
                    context.last_error = e
                    _error_manager.record_error(func.__name__, e)

                    if any(isinstance(e, exc_type) for exc_type in config.stop_on):
                        raise

                    if not any(isinstance(e, exc_type) for exc_type in config.retry_on):
                        raise

                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}: {e}"
                        )
                        raise

                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    if config.jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds"
                    )

                    time.sleep(delay)

            raise context.last_error

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def with_circuit_breaker(operation_name: str = None):
    """Decorator for circuit breaker protection."""

    def decorator(func):
        op_name = operation_name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            circuit_breaker = _error_manager.get_circuit_breaker(op_name)

            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: circuit_breaker.call(func, *args, **kwargs)
                )
                return result
            except Exception as e:
                _error_manager.record_error(op_name, e)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            circuit_breaker = _error_manager.get_circuit_breaker(op_name)

            try:
                return circuit_breaker.call(func, *args, **kwargs)
            except Exception as e:
                _error_manager.record_error(op_name, e)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def with_fallback(fallback_func: Callable):
    """Decorator for fallback functionality."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Primary function {func.__name__} failed: {e}. Using fallback."
                )
                _error_manager.record_error(func.__name__, e)

                try:
                    if asyncio.iscoroutinefunction(fallback_func):
                        return await fallback_func(*args, **kwargs)
                    else:
                        return fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback function also failed: {fallback_error}"
                    )
                    raise e  # Raise original error

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Primary function {func.__name__} failed: {e}. Using fallback."
                )
                _error_manager.record_error(func.__name__, e)

                try:
                    return fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback function also failed: {fallback_error}"
                    )
                    raise e

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class GracefulDegradation:
    """Manages graceful degradation strategies."""

    def __init__(self):
        self.degradation_levels = {
            "full": {"quality_threshold": 0.9, "features": ["all"]},
            "high": {"quality_threshold": 0.8, "features": ["clustering", "citations", "validation"]},
            "medium": {"quality_threshold": 0.6, "features": ["basic_summary", "deduplication"]},
            "minimal": {"quality_threshold": 0.3, "features": ["basic_summary"]},
            "emergency": {"quality_threshold": 0.0, "features": ["fallback_summary"]}
        }

        self.current_level = "full"
        self.error_count = 0
        self.last_degradation = None

    def should_degrade(self, error_rate: float, system_load: float = 1.0) -> bool:
        """Determine if system should degrade."""
        if error_rate > 0.5 or system_load > 0.9:
            return True

        # Check recent errors
        self.error_count += 1
        if self.error_count > 10:
            return True

        return False

    def get_degraded_config(self, target_level: str = None) -> dict[str, Any]:
        """Get configuration for degraded operation."""
        if target_level is None:
            # Auto-select degradation level
            if self.error_count > 20:
                target_level = "emergency"
            elif self.error_count > 15:
                target_level = "minimal"
            elif self.error_count > 10:
                target_level = "medium"
            else:
                target_level = "high"

        self.current_level = target_level
        self.last_degradation = datetime.now()

        config = self.degradation_levels[target_level]

        logger.warning(
            f"System degraded to level: {target_level}",
            quality_threshold=config["quality_threshold"],
            enabled_features=config["features"]
        )

        return config

    def reset_degradation(self):
        """Reset to full operation."""
        if self.current_level != "full":
            logger.info("System restored to full operation")
            self.current_level = "full"
            self.error_count = 0


# Global degradation manager
_degradation_manager = GracefulDegradation()


def get_error_summary() -> dict[str, Any]:
    """Get comprehensive error summary."""
    summary = {
        "error_patterns": {},
        "circuit_breaker_states": {},
        "degradation_status": {
            "current_level": _degradation_manager.current_level,
            "error_count": _degradation_manager.error_count,
            "last_degradation": _degradation_manager.last_degradation
        },
        "recommendations": []
    }

    # Analyze error patterns
    for operation, errors in _error_manager.error_patterns.items():
        if errors:
            recent_errors = [
                e for e in errors
                if datetime.fromisoformat(e["timestamp"]) > datetime.now() - timedelta(hours=1)
            ]

            summary["error_patterns"][operation] = {
                "total_errors": len(errors),
                "recent_errors": len(recent_errors),
                "common_error_types": {},
                "last_error": errors[-1] if errors else None
            }

            # Count error types
            error_types = {}
            for error in recent_errors:
                error_type = error["error_type"]
                error_types[error_type] = error_types.get(error_type, 0) + 1

            summary["error_patterns"][operation]["common_error_types"] = error_types

    # Circuit breaker states
    for operation, cb in _error_manager.circuit_breakers.items():
        summary["circuit_breaker_states"][operation] = {
            "state": cb.state.value,
            "failure_count": cb.failure_count,
            "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
        }

    # Generate recommendations
    recommendations = []

    for operation, pattern in summary["error_patterns"].items():
        if pattern["recent_errors"] > 5:
            recommendations.append(
                f"High error rate in {operation}: {pattern['recent_errors']} errors in last hour"
            )

    if _degradation_manager.current_level != "full":
        recommendations.append(
            f"System is degraded to {_degradation_manager.current_level} level"
        )

    summary["recommendations"] = recommendations

    return summary
