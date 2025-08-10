"""
Publishing workflow node for Quaily platform integration.

This module contains the publishing phase node of the newsletter workflow:
- Quaily platform publishing
- Success rate monitoring
- Publish history tracking
"""

import time
from typing import Union

from src.models.schemas import ProcessingLog
from src.utils.logger import setup_logging

logger = setup_logging()


class PublishingNode:
    """Publishing workflow node for Quaily platform integration."""
    
    def __init__(self):
        """Initialize publishing node."""
        from src.config.settings import get_settings
        self.settings = get_settings()
    
    async def publish_to_quaily_node(self, state: dict) -> dict:
        """Publish the generated newsletter Markdown file to Quaily platform."""
        
        logger.info("Starting Quaily publish node")
        start_time = time.time()
        
        try:
            from src.utils.quaily_client import publish_newsletter
            
            config = state["config"]
            output_file: Union[str, None] = state.get("output_file")
            
            if not output_file:
                logger.warning("No output file produced – skipping Quaily publish step")
                return {**state, "status": "no_output_to_publish"}
            
            # Skip if publishing is disabled
            if not config.publish_enabled:
                logger.info("Quaily publish disabled via configuration – skipping")
                skip_log = ProcessingLog(
                    processing_id=config.processing_id,
                    timestamp=time.time(),
                    stage="publish_to_quaily",
                    event_type="info",
                    message="Publishing disabled (publish_enabled=False)",
                    duration_seconds=time.time() - start_time,
                )
                return {
                    **state,
                    "processing_logs": state["processing_logs"] + [skip_log],
                    "status": "quaily_publish_disabled",
                }
            
            # Perform publish – respect dry_run flag
            publish_result = publish_newsletter(
                file_path=output_file,
                edition=config.edition,
                dry_run=config.dry_run,
            )
            
            processing_time = time.time() - start_time
            
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="publish_to_quaily",
                event_type="info" if publish_result.get("status") == "success" else "warning",
                message=f"Quaily publish status: {publish_result.get('status')}",
                data=publish_result,
                duration_seconds=processing_time,
            )
            
            # Record history for monitoring
            try:
                from src.utils.history_logger import record_publish
                record_publish(config.processing_id, publish_result)
            except Exception as hist_err:  # pylint: disable=broad-except
                logger.warning("Failed to record publish history", error=str(hist_err))
            
            # Compute recent success rate and attach to logs
            try:
                from src.utils.history_logger import compute_success_rate
                success_rate = compute_success_rate(self.settings.workflow.success_rate_history_limit)
                logger.info(f"Current publish success rate (last {self.settings.workflow.success_rate_history_limit})", rate=f"{success_rate:.1f}%")
            except Exception:
                pass
            
            return {
                **state,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "quaily_published" if publish_result.get("status") == "success" else "quaily_publish_skipped",
            }
            
        except Exception as e:
            logger.error("Publish to Quaily node failed", error=str(e))
            
            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="publish_to_quaily",
                event_type="error",
                message=f"Failed to publish to Quaily: {str(e)}",
                duration_seconds=time.time() - start_time,
            )
            
            return {
                **state,
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "quaily_publish_failed",
            }