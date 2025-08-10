"""
FIXED: Newsletter workflow with comprehensive memory management.

This demonstrates proper resource management in workflows:
- Automatic resource tracking and cleanup
- Memory monitoring during execution
- Proper component lifecycle management
- Resource leak prevention
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, END

from src.config.settings import get_settings
from src.models.schemas import WorkflowState
from src.utils.memory_manager import get_memory_manager, track_memory_usage
from src.workflow.nodes.content_processing import ContentProcessingNodes
from src.workflow.nodes.analysis_nodes import AnalysisNodes  
from src.workflow.nodes.generation_nodes import GenerationNodes
from src.workflow.nodes.publishing_node import PublishingNode

logger = logging.getLogger(__name__)


class NewsletterWorkflowFixed:
    """Fixed newsletter workflow with comprehensive memory management."""
    
    def __init__(self):
        """Initialize workflow with memory management."""
        self.settings = get_settings()
        self.memory_manager = get_memory_manager()
        
        # Initialize node components with lifecycle management
        self.content_nodes: Optional[ContentProcessingNodes] = None
        self.analysis_nodes: Optional[AnalysisNodes] = None
        self.generation_nodes: Optional[GenerationNodes] = None
        self.publishing_node: Optional[PublishingNode] = None
        
        # Track workflow execution
        self.is_executing = False
        self.execution_id: Optional[str] = None
        
        logger.info("NewsletterWorkflowFixed initialized")
    
    def _initialize_nodes(self):
        """Initialize workflow nodes with memory tracking."""
        if self.content_nodes is None:
            with self.memory_manager.track_memory_usage("ContentProcessingNodes initialization"):
                self.content_nodes = ContentProcessingNodes()
                self.memory_manager.track_large_object(self.content_nodes)
        
        if self.analysis_nodes is None:
            with self.memory_manager.track_memory_usage("AnalysisNodes initialization"):
                self.analysis_nodes = AnalysisNodes()
                self.memory_manager.track_large_object(self.analysis_nodes)
                
                # Track analysis node caches
                if hasattr(self.analysis_nodes, 'duplicate_checker'):
                    if hasattr(self.analysis_nodes.duplicate_checker, '_article_cache'):
                        self.memory_manager.track_cache_object(
                            self.analysis_nodes.duplicate_checker._article_cache
                        )
        
        if self.generation_nodes is None:
            with self.memory_manager.track_memory_usage("GenerationNodes initialization"):
                self.generation_nodes = GenerationNodes()
                self.memory_manager.track_large_object(self.generation_nodes)
        
        if self.publishing_node is None:
            with self.memory_manager.track_memory_usage("PublishingNode initialization"):
                self.publishing_node = PublishingNode()
                self.memory_manager.track_large_object(self.publishing_node)
    
    @track_memory_usage("newsletter_workflow_execution")
    async def run_workflow(
        self,
        max_items: int = 30,
        edition: str = "daily",
        target_date: Optional[str] = None,
        output_dir: str = "drafts"
    ) -> Dict[str, Any]:
        """Execute newsletter workflow with memory management."""
        
        # Set execution state
        self.is_executing = True
        self.execution_id = f"{edition}_{target_date or 'current'}"
        
        try:
            # Start memory monitoring
            self.memory_manager.start_monitoring(interval=30.0)
            
            # Initialize nodes with memory tracking
            logger.info("Initializing workflow nodes...")
            self._initialize_nodes()
            
            # Create workflow graph
            workflow = self._create_workflow_graph()
            
            # Prepare initial state with memory-aware configuration
            initial_state = WorkflowState(
                max_items=max_items,
                edition=edition,
                target_date=target_date,
                output_dir=output_dir,
                processing_metadata={
                    "execution_id": self.execution_id,
                    "memory_monitoring": True,
                    "cleanup_enabled": True
                }
            )
            
            logger.info(f"Starting newsletter workflow: {self.execution_id}")
            
            # Execute workflow with periodic memory checks
            result = await self._execute_with_memory_monitoring(workflow, initial_state)
            
            logger.info(f"Newsletter workflow completed: {self.execution_id}")
            return result
            
        except Exception as e:
            logger.error(f"Newsletter workflow failed: {e}")
            raise
            
        finally:
            # Always cleanup regardless of success/failure
            await self._cleanup_workflow_resources()
            self.memory_manager.stop_monitoring()
            self.is_executing = False
            self.execution_id = None
    
    async def _execute_with_memory_monitoring(
        self, 
        workflow: StateGraph, 
        initial_state: WorkflowState
    ) -> Dict[str, Any]:
        """Execute workflow with periodic memory monitoring."""
        
        # Define memory checkpoints during workflow execution
        memory_checkpoints = [
            "fetch_sources",
            "filter_ai_content", 
            "generate_summaries",
            "check_duplicates",
            "cluster_topics",
            "generate_newsletter"
        ]
        
        # Wrapper to add memory monitoring to workflow execution
        async def monitored_execution():
            checkpoint_count = 0
            
            async for state_update in workflow.astream(initial_state):
                # Get current node name if available
                current_node = getattr(state_update, 'current_node', 'unknown')
                
                # Periodic memory checks
                if current_node in memory_checkpoints:
                    checkpoint_count += 1
                    current_memory = self.memory_manager._get_memory_stats()
                    
                    logger.info(
                        f"Memory checkpoint {checkpoint_count} [{current_node}]: "
                        f"{current_memory.rss_mb:.1f}MB RSS, "
                        f"{current_memory.open_files} files"
                    )
                    
                    # Force cleanup if memory usage is high
                    if current_memory.rss_mb > 1024:  # 1GB threshold
                        logger.warning("High memory usage detected, forcing cleanup")
                        await self._force_intermediate_cleanup()
                
                yield state_update
        
        # Collect final result
        final_state = None
        async for state in monitored_execution():
            final_state = state
        
        return final_state or {}
    
    async def _force_intermediate_cleanup(self):
        """Force cleanup during workflow execution to prevent memory issues."""
        logger.info("Performing intermediate memory cleanup")
        
        try:
            # Clean up analysis node caches
            if self.analysis_nodes and hasattr(self.analysis_nodes, 'duplicate_checker'):
                if hasattr(self.analysis_nodes.duplicate_checker, '_article_cache'):
                    cache_size = len(self.analysis_nodes.duplicate_checker._article_cache)
                    self.analysis_nodes.duplicate_checker._article_cache.clear()
                    logger.info(f"Cleared duplicate checker cache: {cache_size} entries")
            
            # Clean up embedding manager if available
            if hasattr(self.analysis_nodes, 'context_analyzer'):
                if hasattr(self.analysis_nodes.context_analyzer, 'embedding_manager'):
                    self.analysis_nodes.context_analyzer.embedding_manager.cleanup_resources()
                    logger.info("Cleaned up embedding manager resources")
            
            # Force garbage collection
            self.memory_manager.force_garbage_collection()
            
        except Exception as e:
            logger.warning(f"Intermediate cleanup failed: {e}")
    
    def _create_workflow_graph(self) -> StateGraph:
        """Create workflow graph with memory-aware configuration."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes with memory tracking
        workflow.add_node("fetch_sources", self._wrap_node_with_memory_tracking(
            self.content_nodes.fetch_sources_node, "fetch_sources"
        ))
        workflow.add_node("filter_ai_content", self._wrap_node_with_memory_tracking(
            self.content_nodes.filter_ai_content_node, "filter_ai_content"
        ))
        workflow.add_node("generate_summaries", self._wrap_node_with_memory_tracking(
            self.content_nodes.generate_summaries_node, "generate_summaries"
        ))
        workflow.add_node("check_duplicates", self._wrap_node_with_memory_tracking(
            self.analysis_nodes.check_duplicates_node, "check_duplicates"
        ))
        workflow.add_node("analyze_context", self._wrap_node_with_memory_tracking(
            self.analysis_nodes.analyze_context_node, "analyze_context"
        ))
        workflow.add_node("cluster_topics", self._wrap_node_with_memory_tracking(
            self.analysis_nodes.cluster_topics_node, "cluster_topics"
        ))
        workflow.add_node("process_images", self._wrap_node_with_memory_tracking(
            self.generation_nodes.process_images_node, "process_images"
        ))
        workflow.add_node("generate_newsletter", self._wrap_node_with_memory_tracking(
            self.generation_nodes.generate_newsletter_node, "generate_newsletter"
        ))
        workflow.add_node("publish_newsletter", self._wrap_node_with_memory_tracking(
            self.publishing_node.publish_to_quaily_node, "publish_newsletter"
        ))
        
        # Define edges
        workflow.set_entry_point("fetch_sources")
        workflow.add_edge("fetch_sources", "filter_ai_content")
        workflow.add_edge("filter_ai_content", "generate_summaries")
        workflow.add_edge("generate_summaries", "check_duplicates")
        workflow.add_edge("check_duplicates", "analyze_context")
        workflow.add_edge("analyze_context", "cluster_topics")
        workflow.add_edge("cluster_topics", "process_images")
        workflow.add_edge("process_images", "generate_newsletter")
        workflow.add_edge("generate_newsletter", "publish_newsletter")
        workflow.add_edge("publish_newsletter", END)
        
        return workflow.compile()
    
    def _wrap_node_with_memory_tracking(self, node_func, node_name: str):
        """Wrap node function with memory tracking."""
        async def wrapped_node(state: WorkflowState) -> WorkflowState:
            with self.memory_manager.track_memory_usage(f"workflow_node_{node_name}"):
                # Add current node to state for monitoring
                state.current_node = node_name
                
                # Execute original node
                result = await node_func(state)
                
                # Log memory usage after node execution
                current_memory = self.memory_manager._get_memory_stats()
                logger.debug(f"Node {node_name} completed: {current_memory.rss_mb:.1f}MB RSS")
                
                return result
        
        return wrapped_node
    
    async def _cleanup_workflow_resources(self) -> None:
        """Comprehensive cleanup of workflow resources."""
        logger.info("Starting comprehensive workflow cleanup")
        
        try:
            # Get memory stats before cleanup
            memory_stats_before = self.memory_manager._get_memory_stats()
            
            # Clean up embedding manager resources
            if (self.analysis_nodes and 
                hasattr(self.analysis_nodes, 'context_analyzer') and
                hasattr(self.analysis_nodes.context_analyzer, 'embedding_manager')):
                
                self.analysis_nodes.context_analyzer.embedding_manager.cleanup_resources()
                logger.info("EmbeddingManager resources cleaned up")
            
            # Clean up LLM client caches
            if (self.content_nodes and 
                hasattr(self.content_nodes, 'llm_router') and
                hasattr(self.content_nodes.llm_router, '_clients')):
                
                client_count = len(self.content_nodes.llm_router._clients)
                self.content_nodes.llm_router._clients.clear()
                logger.info(f"Cleared {client_count} LLM client cache entries")
            
            # Clean up analysis node caches
            if self.analysis_nodes:
                if hasattr(self.analysis_nodes, 'context_analyzer'):
                    self.analysis_nodes.context_analyzer = None
                    
                if hasattr(self.analysis_nodes, 'duplicate_checker'):
                    if hasattr(self.analysis_nodes.duplicate_checker, '_article_cache'):
                        self.analysis_nodes.duplicate_checker._article_cache.clear()
            
            # Clean up generation nodes
            if self.generation_nodes:
                if hasattr(self.generation_nodes, '_cleanup_generation_resources'):
                    self.generation_nodes._cleanup_generation_resources()
            
            # Clean up image processing temporary files
            if (self.generation_nodes and 
                hasattr(self.generation_nodes, 'image_processor')):
                # Force cleanup of any remaining temp files
                self.memory_manager.cleanup_temp_files()
            
            # Run global memory manager cleanup
            self.memory_manager.cleanup_all_resources()
            
            # Clear node references
            self.content_nodes = None
            self.analysis_nodes = None
            self.generation_nodes = None
            self.publishing_node = None
            
            # Log memory savings
            memory_stats_after = self.memory_manager._get_memory_stats()
            memory_freed = memory_stats_before.rss_mb - memory_stats_after.rss_mb
            
            logger.info(
                f"Workflow cleanup completed: "
                f"{memory_stats_before.rss_mb:.1f}MB → {memory_stats_after.rss_mb:.1f}MB "
                f"(freed {memory_freed:.1f}MB)"
            )
            
        except Exception as e:
            logger.warning(f"Error during workflow cleanup: {e}")
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory usage report for the workflow."""
        report = self.memory_manager.get_memory_report()
        
        # Add workflow-specific information
        report["workflow"] = {
            "is_executing": self.is_executing,
            "execution_id": self.execution_id,
            "nodes_initialized": {
                "content_nodes": self.content_nodes is not None,
                "analysis_nodes": self.analysis_nodes is not None,
                "generation_nodes": self.generation_nodes is not None,
                "publishing_node": self.publishing_node is not None
            }
        }
        
        return report
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            if self.is_executing:
                logger.warning("Workflow being destroyed while executing - forcing cleanup")
                asyncio.create_task(self._cleanup_workflow_resources())
        except Exception:
            pass  # Ignore errors in destructor


def create_newsletter_workflow_fixed() -> StateGraph:
    """Create and compile the fixed newsletter generation workflow."""
    workflow_manager = NewsletterWorkflowFixed()
    return workflow_manager._create_workflow_graph()


# === WORKFLOW FACTORY WITH MEMORY MANAGEMENT ===

class WorkflowFactory:
    """Factory for creating workflows with proper resource management."""
    
    _instances = {}
    
    @classmethod
    def get_workflow(cls, workflow_type: str = "newsletter") -> NewsletterWorkflowFixed:
        """Get or create workflow instance with singleton pattern for resource efficiency."""
        if workflow_type not in cls._instances:
            cls._instances[workflow_type] = NewsletterWorkflowFixed()
            
            # Register cleanup callback
            memory_manager = get_memory_manager()
            memory_manager.add_cleanup_callback(
                lambda: cls._cleanup_workflow_instances()
            )
        
        return cls._instances[workflow_type]
    
    @classmethod
    def _cleanup_workflow_instances(cls):
        """Clean up all workflow instances."""
        for workflow_type, instance in cls._instances.items():
            try:
                if hasattr(instance, '_cleanup_workflow_resources'):
                    asyncio.create_task(instance._cleanup_workflow_resources())
            except Exception as e:
                logger.warning(f"Failed to cleanup workflow {workflow_type}: {e}")
        
        cls._instances.clear()
        logger.info("All workflow instances cleaned up")


# === USAGE EXAMPLE ===

async def run_newsletter_workflow_with_memory_management(
    max_items: int = 30,
    edition: str = "daily"
) -> Dict[str, Any]:
    """Example of running workflow with comprehensive memory management."""
    
    # Use context manager for automatic cleanup
    with get_memory_manager() as memory_mgr:
        workflow = WorkflowFactory.get_workflow("newsletter")
        
        try:
            result = await workflow.run_workflow(
                max_items=max_items,
                edition=edition
            )
            
            # Log final memory report
            memory_mgr.log_memory_report()
            
            return result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise
        
        # Cleanup is automatic via context manager