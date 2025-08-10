"""
LangGraph workflow for newsletter generation.

This module defines the complete workflow for generating AI news newsletters
using LangGraph state management and node-based processing.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from src.config.settings import get_settings
from src.models.schemas import WorkflowState
from src.utils.memory_manager import get_memory_manager, track_memory_usage
from src.llm.llm_router import LLMRouter
from src.utils.embedding_manager import EmbeddingManager
from src.utils.logger import setup_logging
from src.workflow.nodes.content_processing import ContentProcessingNodes
from src.workflow.nodes.analysis_nodes import AnalysisNodes
from src.workflow.nodes.generation_nodes import GenerationNodes
from src.workflow.nodes.publishing_node import PublishingNode

logger = setup_logging()


class NewsletterWorkflow:
    """LangGraph workflow for newsletter generation with comprehensive memory management."""
    
    def __init__(self):
        """Initialize workflow with memory management."""
        self.settings = get_settings()
        self.memory_manager = get_memory_manager()
        
        # Initialize node components with lifecycle management
        self.content_nodes: Optional[ContentProcessingNodes] = None
        self.analysis_nodes: Optional[AnalysisNodes] = None
        self.generation_nodes: Optional[GenerationNodes] = None
        self.publishing_node: Optional[PublishingNode] = None
        self.embedding_manager: Optional[EmbeddingManager] = None
        
        # Track workflow execution
        self.is_executing = False
        self.execution_id: Optional[str] = None
        
        logger.info("NewsletterWorkflow initialized with memory management")
    
    def _initialize_nodes(self):
        """Initialize workflow nodes with memory tracking."""
        if self.content_nodes is None:
            with self.memory_manager.track_memory_usage("ContentProcessingNodes initialization"):
                self.content_nodes = ContentProcessingNodes()
                self.memory_manager.track_large_object(self.content_nodes)
        
        if self.analysis_nodes is None:
            with self.memory_manager.track_memory_usage("AnalysisNodes initialization"):
                llm_router = LLMRouter()
                self.analysis_nodes = AnalysisNodes(llm_router)
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

    async def initialize_with_past_articles(self, days_back: int = 7):
        """
        Initialize workflow with past articles from Supabase.

        Args:
            days_back: Number of days of past articles to load
        """
        try:
            # Initialize nodes first
            self._initialize_nodes()
            
            # Initialize embedding manager if not already done
            if self.embedding_manager is None:
                with self.memory_manager.track_memory_usage("EmbeddingManager initialization"):
                    self.embedding_manager = EmbeddingManager()
                    self.memory_manager.track_large_object(self.embedding_manager)

            # Sync with Supabase to load past articles
            logger.info(f"Syncing past {days_back} days of articles from Supabase")
            synced_count = await self.embedding_manager.sync_with_supabase(days_back)

            # Also load past articles into duplicate checker's cache
            from src.utils.supabase_client import get_recent_contextual_articles
            past_articles = await get_recent_contextual_articles(
                days_back=days_back,
                limit=1000
            )

            if past_articles:
                logger.info(f"Loading {len(past_articles)} past articles into duplicate checker cache")

            logger.info(
                f"Workflow initialized with {synced_count} articles in embedding index"
            )

        except Exception as e:
            logger.error(f"Failed to initialize with past articles: {e}")
            # Continue without past articles rather than failing completely

    # Workflow node delegation methods with memory tracking
    
    async def fetch_sources_node(self, state: dict) -> dict:
        """Delegate to content processing nodes."""
        self._initialize_nodes()
        with self.memory_manager.track_memory_usage("fetch_sources_node"):
            return await self.content_nodes.fetch_sources_node(state)

    async def filter_ai_content_node(self, state: dict) -> dict:
        """Delegate to content processing nodes."""
        self._initialize_nodes()
        with self.memory_manager.track_memory_usage("filter_ai_content_node"):
            return await self.content_nodes.filter_ai_content_node(state)

    async def generate_summaries_node(self, state: dict) -> dict:
        """Delegate to content processing nodes."""
        self._initialize_nodes()
        with self.memory_manager.track_memory_usage("generate_summaries_node"):
            return await self.content_nodes.generate_summaries_node(state)

    async def check_duplicates_node(self, state: dict) -> dict:
        """Delegate to analysis nodes."""
        self._initialize_nodes()
        with self.memory_manager.track_memory_usage("check_duplicates_node"):
            return await self.analysis_nodes.check_duplicates_node(state)

    async def cluster_topics_node(self, state: dict) -> dict:
        """Delegate to analysis nodes."""
        self._initialize_nodes()
        with self.memory_manager.track_memory_usage("cluster_topics_node"):
            return await self.analysis_nodes.cluster_topics_node(state)

    async def process_images_node(self, state: dict) -> dict:
        """Delegate to generation nodes."""
        self._initialize_nodes()
        with self.memory_manager.track_memory_usage("process_images_node"):
            return await self.generation_nodes.process_images_node(state)

    async def generate_newsletter_node(self, state: dict) -> dict:
        """Delegate to generation nodes."""
        self._initialize_nodes()
        with self.memory_manager.track_memory_usage("generate_newsletter_node"):
            return await self.generation_nodes.generate_newsletter_node(state)

    async def publish_to_quaily_node(self, state: dict) -> dict:
        """Delegate to publishing node."""
        self._initialize_nodes()
        with self.memory_manager.track_memory_usage("publish_to_quaily_node"):
            return await self.publishing_node.publish_to_quaily_node(state)

    # Shared utility methods

    def _sort_articles_by_priority(self, articles: list) -> list:
        """
        Sort articles by source priority.

        優先順位:
        1. 公式リリース系 (priority: 1) - 最上位
        2. ニュースレター系 (priority: 2) - 次点
        3. メディア・YouTube系 (priority: 3) - 同列
        4. 日本語系ソース (priority: 4) - 最下位

        Args:
            articles: 記事リスト

        Returns:
            優先順位順にソートされた記事リスト
        """
        from src.constants.source_priorities import get_priority_description

        def get_sort_key(article):
            """Get sorting key for article (priority, then published_date desc)"""
            # Ensure source_priority is set
            if not hasattr(article, 'source_priority') or article.source_priority is None:
                article.set_source_priority()

            # Sort by priority (ascending = higher priority first), then by date (descending = newest first)
            return (article.source_priority, -article.published_date.timestamp())

        sorted_articles = sorted(articles, key=get_sort_key)

        # Log priority distribution for monitoring
        priority_counts = {}
        for article in sorted_articles:
            priority = getattr(article, 'source_priority', 3)
            priority_desc = get_priority_description(priority)
            priority_counts[priority_desc] = priority_counts.get(priority_desc, 0) + 1

        logger.info(
            "Article priority distribution after sorting",
            total_articles=len(sorted_articles),
            priority_distribution=priority_counts,
            top_sources=[{
                "source_id": article.source_id,
                "priority": getattr(article, 'source_priority', 3),
                "title": article.title[:50] + "..." if len(article.title) > 50 else article.title
            } for article in sorted_articles[:5]]  # Log top 5 articles
        )

        return sorted_articles

    async def _cleanup_workflow_resources(self) -> None:
        """Comprehensive cleanup of workflow resources."""
        logger.info("Starting comprehensive workflow cleanup")
        
        try:
            # Get memory stats before cleanup
            memory_stats_before = self.memory_manager._get_memory_stats()
            
            # Clean up embedding manager resources
            if (self.embedding_manager):
                self.embedding_manager.cleanup_resources()
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
            self.embedding_manager = None
            
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
                "publishing_node": self.publishing_node is not None,
                "embedding_manager": self.embedding_manager is not None
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


def create_newsletter_workflow() -> StateGraph:
    """Create and compile the newsletter generation workflow."""

    workflow_instance = NewsletterWorkflow()

    # Create state graph
    workflow = StateGraph(dict)  # Use dict instead of NewsletterState for LangGraph compatibility

    # Add nodes
    workflow.add_node("fetch_sources", workflow_instance.fetch_sources_node)
    workflow.add_node("filter_ai_content", workflow_instance.filter_ai_content_node)
    workflow.add_node("generate_summaries", workflow_instance.generate_summaries_node)
    workflow.add_node("check_duplicates", workflow_instance.check_duplicates_node)
    workflow.add_node("cluster_topics", workflow_instance.cluster_topics_node)
    workflow.add_node("process_images", workflow_instance.process_images_node)
    workflow.add_node("generate_newsletter", workflow_instance.generate_newsletter_node)
    workflow.add_node("publish_to_quaily", workflow_instance.publish_to_quaily_node)

    # Add edges (sequential flow)
    workflow.add_edge("fetch_sources", "filter_ai_content")
    workflow.add_edge("filter_ai_content", "generate_summaries")
    workflow.add_edge("generate_summaries", "check_duplicates")
    workflow.add_edge("check_duplicates", "cluster_topics")
    workflow.add_edge("cluster_topics", "process_images")
    workflow.add_edge("process_images", "generate_newsletter")
    workflow.add_edge("generate_newsletter", "publish_to_quaily")
    workflow.add_edge("publish_to_quaily", END)

    # Set entry point
    workflow.set_entry_point("fetch_sources")

    return workflow.compile()