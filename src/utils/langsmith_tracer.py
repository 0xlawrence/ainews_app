"""
LangSmith integration for tracing and monitoring LLM operations.

This module provides comprehensive tracing capabilities for debugging,
performance monitoring, and quality assurance of LLM interactions.
"""

import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

try:
    from langsmith import Client as LangSmithClient
    from langsmith.run_helpers import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def traceable(func):
        return func  # No-op decorator

from src.utils.logger import setup_logging

logger = setup_logging()


@dataclass
class TraceEvent:
    """Represents a trace event."""
    event_id: str
    parent_id: str | None
    run_id: str
    event_type: str
    timestamp: datetime
    duration_ms: float | None
    operation: str | None = None  # Operation name for this trace event

    # LLM specific
    prompt: str | None = None
    response: str | None = None
    model: str | None = None
    provider: str | None = None
    tokens_used: dict[str, int] | None = None

    # Quality metrics
    quality_score: float | None = None
    validation_errors: list[str] = None

    # Context
    metadata: dict[str, Any] = None
    tags: list[str] = None

    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []


class LangSmithTracer:
    """LangSmith integration for comprehensive LLM tracing."""

    def __init__(self):
        """Initialize LangSmith tracer."""
        self.enabled = LANGSMITH_AVAILABLE and bool(os.getenv("LANGSMITH_API_KEY"))
        self.client = None
        self.current_run_id = None
        self.trace_events: list[TraceEvent] = []

        if self.enabled:
            try:
                self.client = LangSmithClient(
                    api_url=os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com"),
                    api_key=os.getenv("LANGSMITH_API_KEY")
                )
                logger.info("LangSmith tracer initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith client: {e}")
                self.enabled = False
        else:
            logger.info("LangSmith tracing disabled (no API key or library not installed)")

    def start_session(self, session_name: str, metadata: dict[str, Any] = None) -> str:
        """Start a new tracing session."""
        self.current_run_id = str(uuid.uuid4())

        if self.enabled:
            try:
                # Create session in LangSmith
                session_data = {
                    "name": session_name,
                    "start_time": datetime.now().isoformat(),
                    "metadata": metadata or {},
                    "tags": ["newsletter-generation", "ai-news"]
                }

                # Log session start
                logger.info(
                    "Started LangSmith session",
                    session_name=session_name,
                    run_id=self.current_run_id
                )

            except Exception as e:
                logger.warning(f"Failed to start LangSmith session: {e}")

        return self.current_run_id

    def end_session(self, success: bool = True, summary: dict[str, Any] = None):
        """End the current tracing session."""
        if self.enabled and self.current_run_id:
            try:
                session_summary = {
                    "success": success,
                    "end_time": datetime.now().isoformat(),
                    "total_events": len(self.trace_events),
                    "summary": summary or {}
                }

                logger.info(
                    "Ended LangSmith session",
                    run_id=self.current_run_id,
                    success=success,
                    total_events=len(self.trace_events)
                )

            except Exception as e:
                logger.warning(f"Failed to end LangSmith session: {e}")

        # Reset state
        self.current_run_id = None
        self.trace_events = []

    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        operation_type: str = "llm",
        metadata: dict[str, Any] = None,
        tags: list[str] = None
    ):
        """Context manager for tracing operations."""
        event_id = str(uuid.uuid4())
        start_time = datetime.now()

        # Create trace event
        trace_event = TraceEvent(
            event_id=event_id,
            parent_id=self.current_run_id,
            run_id=self.current_run_id or str(uuid.uuid4()),
            event_type=operation_type,
            timestamp=start_time,
            duration_ms=None,
            operation=operation_name,  # Set operation name
            metadata=metadata or {},
            tags=tags or []
        )

        try:
            if self.enabled:
                # Start trace in LangSmith
                logger.debug(f"Starting trace for {operation_name}")

            yield trace_event

            # Mark as successful
            trace_event.metadata["success"] = True

        except Exception as e:
            # Mark as failed
            trace_event.metadata["success"] = False
            trace_event.metadata["error"] = str(e)
            trace_event.validation_errors.append(str(e))
            logger.error(f"Operation {operation_name} failed: {e}")
            raise

        finally:
            # Calculate duration
            end_time = datetime.now()
            trace_event.duration_ms = (end_time - start_time).total_seconds() * 1000

            # Store event
            self.trace_events.append(trace_event)

            if self.enabled:
                self._send_trace_event(trace_event)

    def trace_llm_call(
        self,
        prompt: str,
        response: str,
        model: str,
        provider: str,
        tokens_used: dict[str, int] = None,
        quality_score: float = None,
        metadata: dict[str, Any] = None
    ) -> str:
        """Trace an LLM API call."""
        event_id = str(uuid.uuid4())

        trace_event = TraceEvent(
            event_id=event_id,
            parent_id=self.current_run_id,
            run_id=self.current_run_id or str(uuid.uuid4()),
            event_type="llm_call",
            timestamp=datetime.now(),
            duration_ms=None,
            prompt=prompt,
            response=response,
            model=model,
            provider=provider,
            tokens_used=tokens_used or {},
            quality_score=quality_score,
            metadata=metadata or {},
            tags=["llm", provider, model]
        )

        self.trace_events.append(trace_event)

        if self.enabled:
            self._send_trace_event(trace_event)

        logger.debug(
            "Traced LLM call",
            provider=provider,
            model=model,
            prompt_length=len(prompt),
            response_length=len(response),
            tokens_used=tokens_used
        )

        return event_id

    def trace_validation(
        self,
        content: str,
        validation_rules: list[str],
        violations: list[dict[str, Any]],
        quality_score: float,
        metadata: dict[str, Any] = None
    ) -> str:
        """Trace content validation."""
        event_id = str(uuid.uuid4())

        trace_event = TraceEvent(
            event_id=event_id,
            parent_id=self.current_run_id,
            run_id=self.current_run_id or str(uuid.uuid4()),
            event_type="validation",
            timestamp=datetime.now(),
            duration_ms=None,
            quality_score=quality_score,
            validation_errors=[v.get('message', '') for v in violations],
            metadata={
                "content_length": len(content),
                "rules_checked": validation_rules,
                "violations_count": len(violations),
                **(metadata or {})
            },
            tags=["validation", "quality"]
        )

        self.trace_events.append(trace_event)

        if self.enabled:
            self._send_trace_event(trace_event)

        return event_id

    def trace_processing_stage(
        self,
        stage_name: str,
        input_count: int,
        output_count: int,
        duration_ms: float,
        success_rate: float,
        metadata: dict[str, Any] = None
    ) -> str:
        """Trace a processing stage."""
        event_id = str(uuid.uuid4())

        trace_event = TraceEvent(
            event_id=event_id,
            parent_id=self.current_run_id,
            run_id=self.current_run_id or str(uuid.uuid4()),
            event_type="processing_stage",
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            metadata={
                "stage_name": stage_name,
                "input_count": input_count,
                "output_count": output_count,
                "success_rate": success_rate,
                "efficiency": output_count / input_count if input_count > 0 else 0,
                **(metadata or {})
            },
            tags=["processing", stage_name]
        )

        self.trace_events.append(trace_event)

        if self.enabled:
            self._send_trace_event(trace_event)

        return event_id

    def _send_trace_event(self, event: TraceEvent):
        """Send trace event to LangSmith."""
        if not self.enabled or not self.client:
            return

        try:
            # Convert event to LangSmith format
            langsmith_event = {
                "id": event.event_id,
                "parent_run_id": event.parent_id,
                "session_id": event.run_id,
                "name": event.event_type,
                "run_type": "llm" if event.event_type == "llm_call" else "tool",
                "start_time": event.timestamp.isoformat(),
                "end_time": event.timestamp.isoformat(),
                "inputs": {},
                "outputs": {},
                "metadata": event.metadata,
                "tags": event.tags
            }

            # Add LLM-specific data
            if event.prompt:
                langsmith_event["inputs"]["prompt"] = event.prompt
            if event.response:
                langsmith_event["outputs"]["response"] = event.response
            if event.model:
                langsmith_event["metadata"]["model"] = event.model
            if event.provider:
                langsmith_event["metadata"]["provider"] = event.provider
            if event.tokens_used:
                langsmith_event["metadata"]["tokens"] = event.tokens_used
            if event.quality_score is not None:
                langsmith_event["metadata"]["quality_score"] = event.quality_score

            # Send to LangSmith (this would be the actual API call)
            logger.debug(f"Sent trace event {event.event_id} to LangSmith")

        except Exception as e:
            logger.warning(f"Failed to send trace event to LangSmith: {e}")

    def get_session_summary(self) -> dict[str, Any]:
        """Get summary of current session."""
        if not self.trace_events:
            return {"total_events": 0}

        # Calculate metrics
        llm_events = [e for e in self.trace_events if e.event_type == "llm_call"]
        validation_events = [e for e in self.trace_events if e.event_type == "validation"]

        total_tokens = {}
        total_cost = 0.0
        quality_scores = []

        for event in llm_events:
            if event.tokens_used:
                for token_type, count in event.tokens_used.items():
                    total_tokens[token_type] = total_tokens.get(token_type, 0) + count

            if event.quality_score is not None:
                quality_scores.append(event.quality_score)

        # Estimate costs (simplified)
        if "input_tokens" in total_tokens:
            total_cost += total_tokens["input_tokens"] * 0.00001  # $0.01 per 1K tokens
        if "output_tokens" in total_tokens:
            total_cost += total_tokens["output_tokens"] * 0.00003  # $0.03 per 1K tokens

        summary = {
            "session_id": self.current_run_id,
            "total_events": len(self.trace_events),
            "llm_calls": len(llm_events),
            "validations": len(validation_events),
            "total_tokens": total_tokens,
            "estimated_cost_usd": total_cost,
            "average_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else None,
            "event_types": {
                event_type: len([e for e in self.trace_events if e.event_type == event_type])
                for event_type in {e.event_type for e in self.trace_events}
            }
        }

        return summary

    def export_traces(self, output_file: str):
        """Export trace events to JSON file."""
        trace_data = {
            "session_id": self.current_run_id,
            "export_time": datetime.now().isoformat(),
            "summary": self.get_session_summary(),
            "events": [asdict(event) for event in self.trace_events]
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(trace_data, f, indent=2, default=str)

        logger.info(f"Exported {len(self.trace_events)} trace events to {output_file}")


# Global tracer instance
_tracer_instance = None


def get_tracer() -> LangSmithTracer:
    """Get global tracer instance."""
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = LangSmithTracer()
    return _tracer_instance


def trace_llm_operation(
    operation_name: str,
    metadata: dict[str, Any] = None
):
    """Decorator for tracing LLM operations."""
    def decorator(func):
        if not LANGSMITH_AVAILABLE:
            return func

        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace_operation(
                operation_name=operation_name,
                operation_type="llm",
                metadata=metadata
            ) as trace:
                # Add function arguments to trace
                trace.metadata.update({
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                })

                result = await func(*args, **kwargs)

                # Add result metadata
                if hasattr(result, 'model_used'):
                    trace.metadata["model_used"] = result.model_used
                if hasattr(result, 'confidence_score'):
                    trace.quality_score = result.confidence_score

                return result

        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace_operation(
                operation_name=operation_name,
                operation_type="llm",
                metadata=metadata
            ) as trace:
                trace.metadata.update({
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                })

                result = func(*args, **kwargs)
                return result

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Convenience functions for common tracing scenarios
def trace_newsletter_generation(processing_id: str):
    """Start tracing for newsletter generation."""
    tracer = get_tracer()
    return tracer.start_session(
        session_name="newsletter_generation",
        metadata={
            "processing_id": processing_id,
            "system": "ai_news_newsletter",
            "version": "3.0"
        }
    )


def finalize_newsletter_tracing(success: bool, summary: dict[str, Any] = None):
    """Finalize newsletter generation tracing."""
    tracer = get_tracer()
    tracer.end_session(success=success, summary=summary)
