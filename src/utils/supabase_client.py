"""
Supabase client for newsletter data storage.

This module handles database operations for processed content,
processing logs, and article relationships.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

from src.models.schemas import ProcessedArticle, ProcessingLog, SummarizedArticle
from src.utils.logger import setup_logging

logger = setup_logging()


class SupabaseClient:
    """Client for Supabase database operations."""
    
    def __init__(self):
        """Initialize Supabase client."""
        
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase not available - install with: pip install supabase")
            self.client = None
            return
        
        url = os.getenv("SUPABASE_URL")
        # Try service role key first (bypasses RLS), fallback to regular key
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            logger.warning(
                "Supabase credentials not found",
                has_url=bool(url),
                has_key=bool(key),
                using_service_key=bool(os.getenv("SUPABASE_SERVICE_KEY"))
            )
            self.client = None
            return
        
        try:
            self.client: Client = create_client(url, key)
            using_service_key = bool(os.getenv("SUPABASE_SERVICE_KEY"))
            logger.info(
                "Supabase client initialized",
                using_service_key=using_service_key,
                key_type="service_role" if using_service_key else "anon"
            )
        except Exception as e:
            logger.error("Failed to initialize Supabase client", error=str(e))
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Supabase client is available."""
        return self.client is not None
    
    async def save_processed_content(
        self,
        processing_id: str,
        articles: List[ProcessedArticle],
        newsletter_content: str,
        metadata: Dict,
        edition: str = "daily"
    ) -> bool:
        """Save processed newsletter content to database."""
        
        if not self.is_available():
            logger.debug("Supabase not available, skipping content save")
            return False
        
        try:
            # Extract processing date from processing_id or use current date
            processing_date = datetime.now().date()
            if processing_id and len(processing_id) >= 10:
                try:
                    # Assume processing_id format includes date like "2024-01-01_daily_..."
                    date_part = processing_id.split('_')[0]
                    if len(date_part) == 10:  # YYYY-MM-DD format
                        processing_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                except (ValueError, IndexError):
                    pass  # Use current date as fallback
            
            # Prepare data for processed_content table (matching phase2_tables.sql schema)
            content_data = {
                "processing_date": processing_date.isoformat(),
                "edition": edition,
                "content_type": "newsletter",
                "title": f"AI News {edition.title()} - {processing_date.strftime('%Y-%m-%d')}",
                "lead_paragraph": "Generated AI news newsletter",
                "articles_count": len(articles),
                "multi_source_topics": metadata.get("multi_source_topics", 0),
                "content_md": newsletter_content,
                "metadata": {
                    **metadata,
                    "processing_id": processing_id,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # Use upsert to handle potential duplicates based on unique constraint
            try:
                result = self.client.table("processed_content").upsert(
                    content_data,
                    on_conflict="processing_date,edition,content_type"
                ).execute()
            except Exception as upsert_error:
                logger.warning(
                    "Upsert failed, trying regular insert",
                    error=str(upsert_error)
                )
                # Fallback to regular insert
                result = self.client.table("processed_content").insert(content_data).execute()
            
            if result.data:
                logger.info(
                    "Saved processed content to Supabase",
                    processing_id=processing_id,
                    processing_date=processing_date,
                    edition=edition,
                    articles_count=len(articles)
                )
                return True
            else:
                logger.error(
                    "Failed to save processed content", 
                    result=getattr(result, 'error', 'Unknown error'),
                    processing_id=processing_id
                )
                return False
                
        except Exception as e:
            logger.error(
                "Error saving processed content",
                processing_id=processing_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def save_processing_logs(
        self,
        logs: List[ProcessingLog],
        edition: str = "daily"
    ) -> bool:
        """Save processing logs to database."""
        
        if not self.is_available():
            logger.debug("Supabase not available, skipping logs save")
            return False
        
        try:
            if not logs:
                return True
            
            # Aggregate logs into a single processing_logs entry (matching phase2_tables.sql schema)
            processing_date = datetime.now().date()
            
            # Extract processing_id and date from first log
            first_log = logs[0]
            processing_id = getattr(first_log, 'processing_id', None)
            
            if processing_id and len(processing_id) >= 10:
                try:
                    date_part = processing_id.split('_')[0]
                    if len(date_part) == 10:
                        processing_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                except (ValueError, IndexError):
                    pass
            
            # Calculate aggregated metrics
            total_processing_time = sum(
                getattr(log, 'duration_seconds', 0) or 0 for log in logs
            )
            
            # Count articles processed and failed based on log messages
            articles_processed = 0
            articles_failed = 0
            llm_calls = 0
            
            for log in logs:
                if hasattr(log, 'data') and log.data:
                    articles_processed += log.data.get('output_articles', 0)
                    articles_failed += log.data.get('articles_failed', 0)
                    llm_calls += log.data.get('llm_calls', 0)
            
            # Determine overall status
            error_logs = [log for log in logs if getattr(log, 'event_type', '') == 'error']
            if error_logs:
                status = "failed" if len(error_logs) > len(logs) / 2 else "partial"
            else:
                status = "success"
            
            # Prepare aggregated log data
            log_data = {
                "processing_date": processing_date.isoformat(),
                "edition": edition,
                "status": status,
                "articles_processed": articles_processed,
                "articles_failed": articles_failed,
                "llm_calls": llm_calls,
                "total_tokens": 0,  # This would need to be tracked separately
                "processing_time_seconds": total_processing_time,
                "data": {
                    "processing_id": processing_id,
                    "detailed_logs": [
                        {
                            "stage": getattr(log, 'stage', ''),
                            "event_type": getattr(log, 'event_type', ''),
                            "message": getattr(log, 'message', ''),
                            "timestamp": getattr(log, 'timestamp', datetime.now()).isoformat() if hasattr(log, 'timestamp') and log.timestamp else datetime.now().isoformat(),
                            "duration_seconds": getattr(log, 'duration_seconds', 0),
                            "data": getattr(log, 'data', {})
                        }
                        for log in logs
                    ]
                },
                "error_details": "; ".join([
                    getattr(log, 'message', '') for log in error_logs
                ]) if error_logs else None
            }
            
            # Use upsert to handle potential duplicates
            try:
                result = self.client.table("processing_logs").upsert(
                    log_data,
                    on_conflict="processing_date,edition"
                ).execute()
            except Exception as upsert_error:
                logger.warning(
                    "Processing logs upsert failed, trying regular insert",
                    error=str(upsert_error)
                )
                result = self.client.table("processing_logs").insert(log_data).execute()
            
            if result.data:
                logger.info(
                    "Saved aggregated processing logs to Supabase",
                    processing_date=processing_date,
                    edition=edition,
                    status=status,
                    detailed_logs_count=len(logs)
                )
                return True
            else:
                logger.error(
                    "Failed to save processing logs",
                    result=getattr(result, 'error', 'Unknown error'),
                    processing_date=processing_date
                )
                return False
                
        except Exception as e:
            logger.error(
                "Error saving processing logs",
                logs_count=len(logs),
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def get_recent_articles(
        self,
        days_back: int = 7,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent articles for duplicate checking."""
        
        if not self.is_available():
            logger.debug("Supabase not available, returning empty recent articles")
            return []
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_back)
            
            # Query recent articles
            result = self.client.table("processed_content").select(
                "processing_id, created_at, metadata"
            ).gte(
                "created_at", cutoff_date.isoformat()
            ).order(
                "created_at", desc=True
            ).limit(limit).execute()
            
            if result.data:
                logger.info(
                    "Retrieved recent articles from Supabase",
                    count=len(result.data),
                    days_back=days_back
                )
                return result.data
            else:
                logger.info("No recent articles found in Supabase")
                return []
                
        except Exception as e:
            logger.error(
                "Error getting recent articles",
                days_back=days_back,
                error=str(e)
            )
            return []
    
    async def check_health(self) -> Dict[str, bool]:
        """Check Supabase connection health."""
        
        if not self.is_available():
            return {
                "available": False,
                "connected": False,
                "tables_accessible": False,
                "schema_compatible": False
            }
        
        try:
            # Test connection with multiple table queries to verify schema compatibility
            tables_to_check = [
                "processed_content",
                "processing_logs", 
                "contextual_articles",
                "article_relationships"
            ]
            
            tables_accessible = {}
            schema_compatible = True
            
            for table in tables_to_check:
                try:
                    # Test basic connectivity
                    result = self.client.table(table).select("*").limit(1).execute()
                    tables_accessible[table] = result.data is not None
                    
                    # Test specific columns for schema compatibility
                    if table == "processed_content":
                        # Test for required columns in the actual schema
                        test_result = self.client.table(table).select(
                            "processing_date, edition, content_type, articles_count"
                        ).limit(1).execute()
                        if test_result.data is None and hasattr(test_result, 'error'):
                            schema_compatible = False
                            logger.warning(
                                f"Schema compatibility issue with {table}",
                                error=getattr(test_result, 'error', 'Unknown')
                            )
                    
                    elif table == "processing_logs":
                        # Test for required columns
                        test_result = self.client.table(table).select(
                            "processing_date, edition, status, data"
                        ).limit(1).execute()
                        if test_result.data is None and hasattr(test_result, 'error'):
                            schema_compatible = False
                            logger.warning(
                                f"Schema compatibility issue with {table}",
                                error=getattr(test_result, 'error', 'Unknown')
                            )
                            
                except Exception as table_error:
                    logger.warning(
                        f"Table {table} not accessible",
                        error=str(table_error)
                    )
                    tables_accessible[table] = False
                    schema_compatible = False
            
            overall_accessible = any(tables_accessible.values())
            
            health_status = {
                "available": True,
                "connected": True,
                "tables_accessible": overall_accessible,
                "schema_compatible": schema_compatible,
                "table_details": tables_accessible
            }
            
            if not schema_compatible:
                logger.warning(
                    "Supabase schema compatibility issues detected",
                    health_status=health_status
                )
            
            return health_status
            
        except Exception as e:
            logger.error(
                "Supabase health check failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "available": True,
                "connected": False,
                "tables_accessible": False,
                "schema_compatible": False,
                "error": str(e)
            }


# SQL for creating required tables (for reference)\n# NOTE: The schemas below are OUTDATED. Use sql/phase2_tables.sql for the actual database schema.\n# This code has been updated to work with the phase2_tables.sql schema.
REQUIRED_TABLES_SQL = """
-- Processed newsletter content
CREATE TABLE IF NOT EXISTS processed_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processing_id VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    newsletter_content TEXT NOT NULL,
    articles_count INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    status VARCHAR DEFAULT 'completed'
);

-- Processing execution logs
CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processing_id VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    stage VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    duration_seconds FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_processed_content_processing_id ON processed_content(processing_id);
CREATE INDEX IF NOT EXISTS idx_processed_content_created_at ON processed_content(created_at);
CREATE INDEX IF NOT EXISTS idx_processing_logs_processing_id ON processing_logs(processing_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_stage ON processing_logs(stage);
"""


async def get_supabase_client() -> SupabaseClient:
    """Get configured Supabase client."""
    return SupabaseClient()


async def save_newsletter_to_supabase(
    processing_id: str,
    articles: List[ProcessedArticle],
    newsletter_content: str,
    processing_logs: List[ProcessingLog],
    metadata: Dict,
    edition: str = "daily"
) -> bool:
    """
    Convenience function to save newsletter data to Supabase.
    
    Args:
        processing_id: Unique processing identifier
        articles: Processed articles
        newsletter_content: Generated newsletter content
        processing_logs: Processing logs
        metadata: Additional metadata
        edition: Newsletter edition (daily, weekly, etc.)
    
    Returns:
        True if successful, False otherwise
    """
    
    client = await get_supabase_client()
    
    if not client.is_available():
        logger.info("Supabase not available, skipping database save")
        return False
    
    # Add error handling with fallback mechanisms
    content_saved = False
    logs_saved = False
    
    # Try to save content with retries
    for attempt in range(3):
        try:
            content_saved = await client.save_processed_content(
                processing_id, articles, newsletter_content, metadata, edition
            )
            if content_saved:
                break
        except Exception as e:
            logger.warning(
                f"Content save attempt {attempt + 1} failed",
                processing_id=processing_id,
                error=str(e)
            )
            if attempt == 2:  # Last attempt
                logger.error(
                    "All content save attempts failed",
                    processing_id=processing_id,
                    final_error=str(e)
                )
    
    # Try to save logs with retries
    for attempt in range(3):
        try:
            logs_saved = await client.save_processing_logs(processing_logs, edition)
            if logs_saved:
                break
        except Exception as e:
            logger.warning(
                f"Logs save attempt {attempt + 1} failed",
                processing_id=processing_id,
                error=str(e)
            )
            if attempt == 2:  # Last attempt
                logger.error(
                    "All logs save attempts failed",
                    processing_id=processing_id,
                    final_error=str(e)
                )
    
    # Log final results
    if content_saved and logs_saved:
        logger.info(
            "Successfully saved newsletter to Supabase",
            processing_id=processing_id,
            edition=edition
        )
        return True
    elif content_saved or logs_saved:
        logger.warning(
            "Partial save to Supabase",
            processing_id=processing_id,
            edition=edition,
            content_saved=content_saved,
            logs_saved=logs_saved
        )
        return True  # Partial success is still acceptable
    else:
        logger.error(
            "Complete failure to save to Supabase",
            processing_id=processing_id,
            edition=edition
        )
        return False


async def save_contextual_article(
    article: ProcessedArticle,
    embedding: Optional[List[float]] = None,
    topic_cluster: Optional[str] = None,
    client: Optional[SupabaseClient] = None
) -> Optional[str]:
    """
    Save article to contextual_articles table.
    
    Args:
        article: Processed article with all metadata
        embedding: Optional embedding vector
        topic_cluster: Optional topic cluster identifier
        client: Optional existing Supabase client
    
    Returns:
        UUID of saved contextual article or None if failed
    """
    
    if client is None:
        client = await get_supabase_client()
    
    if not client.is_available():
        logger.debug("Supabase not available, skipping contextual article save")
        return None
    
    try:
        raw_article = article.summarized_article.filtered_article.raw_article
        
        # Prepare contextual article data
        contextual_data = {
            "article_id": raw_article.id,
            "title": raw_article.title,
            "content_summary": " ".join(article.summarized_article.summary.summary_points),
            "published_date": raw_article.published_date.isoformat(),
            "source_url": str(raw_article.url),
            "source_id": raw_article.source_id,
            "topic_cluster": topic_cluster,
            "ai_relevance_score": article.summarized_article.filtered_article.ai_relevance_score,
            "summary_points": article.summarized_article.summary.summary_points,  # Store as JSONB
            "japanese_title": getattr(article, 'japanese_title', None),
            "is_update": getattr(article, 'is_update', False),
            "embedding": embedding  # Store embedding directly in contextual_articles
        }
        
        # Upsert contextual article
        result = client.client.table("contextual_articles").upsert(
            contextual_data,
            on_conflict="article_id"
        ).execute()
        
        if result.data:
            logger.info(
                "Saved contextual article to Supabase",
                article_id=raw_article.id,
                has_embedding=bool(embedding)
            )
            return result.data[0]["id"]
        else:
            logger.error("Failed to save contextual article", result=result)
            return None
            
    except Exception as e:
        logger.error(
            "Error saving contextual article",
            article_id=article.summarized_article.filtered_article.raw_article.id,
            error=str(e)
        )
        return None


async def save_article_relationship(
    parent_article_uuid: str,
    child_article_uuid: str,
    relationship_type: str,
    similarity_score: float,
    reasoning: Optional[str] = None,
    client: Optional[SupabaseClient] = None
) -> bool:
    """
    Save article relationship to database.
    
    Args:
        parent_article_uuid: UUID of parent article
        child_article_uuid: UUID of child article
        relationship_type: Type of relationship (sequel, related, update)
        similarity_score: Similarity score between articles
        reasoning: Optional reasoning for the relationship
        client: Optional existing Supabase client
    
    Returns:
        True if successful, False otherwise
    """
    
    if client is None:
        client = await get_supabase_client()
    
    if not client.is_available():
        logger.debug("Supabase not available, skipping relationship save")
        return False
    
    try:
        # Save relationship
        relationship_data = {
            "parent_article_id": parent_article_uuid,
            "child_article_id": child_article_uuid,
            "relationship_type": relationship_type,
            "similarity_score": similarity_score,
            "reasoning": reasoning
        }
        
        result = client.client.table("article_relationships").insert(
            relationship_data
        ).execute()
        
        if result.data:
            logger.info(
                "Saved article relationship",
                parent_uuid=parent_article_uuid,
                child_uuid=child_article_uuid,
                relationship_type=relationship_type,
                similarity_score=similarity_score
            )
            return True
        else:
            logger.error("Failed to save article relationship", result=result)
            return False
            
    except Exception as e:
        logger.error(
            "Error saving article relationship",
            parent_uuid=parent_article_uuid,
            child_uuid=child_article_uuid,
            error=str(e)
        )
        return False


async def get_recent_contextual_articles(
    days_back: int = 7,
    limit: int = 1000,
    client: Optional[SupabaseClient] = None
) -> List[Dict]:
    """
    Get recent contextual articles with embeddings.
    
    Args:
        days_back: Number of days to look back
        limit: Maximum number of articles to return
        client: Optional existing Supabase client
    
    Returns:
        List of contextual articles with metadata
    """
    
    if client is None:
        client = await get_supabase_client()
    
    if not client.is_available():
        logger.debug("Supabase not available, returning empty contextual articles")
        return []
    
    try:
        from datetime import datetime, timedelta
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Query contextual articles with embeddings
        result = client.client.table("contextual_articles").select(
            "id, article_id, title, content_summary, published_date, source_id, "
            "ai_relevance_score, summary_points, japanese_title, is_update, "
            "topic_cluster, embedding"
        ).gte(
            "published_date", cutoff_date.isoformat()
        ).order(
            "published_date", desc=True
        ).limit(limit).execute()
        
        if result.data:
            logger.info(
                "Retrieved contextual articles from Supabase",
                count=len(result.data),
                days_back=days_back
            )
            return result.data
        else:
            logger.info("No contextual articles found in Supabase")
            return []
            
    except Exception as e:
        logger.error(
            "Error getting contextual articles",
            days_back=days_back,
            error=str(e)
        )
        return []


async def find_related_articles_by_id(
    article_id: str,
    max_results: int = 5,
    client: Optional[SupabaseClient] = None
) -> List[Dict]:
    """
    Find articles related to a given article by its ID.
    
    Args:
        article_id: Article ID to find relationships for
        max_results: Maximum number of related articles
        client: Optional existing Supabase client
    
    Returns:
        List of related articles with relationship metadata
    """
    
    if client is None:
        client = await get_supabase_client()
    
    if not client.is_available():
        return []
    
    try:
        # First get the contextual article UUID
        article_result = client.client.table("contextual_articles").select("id").eq(
            "article_id", article_id
        ).execute()
        
        if not article_result.data:
            logger.warning(f"Article not found: {article_id}")
            return []
        
        article_uuid = article_result.data[0]["id"]
        
        # Query relationships (both as parent and child)
        parent_result = client.client.table("article_relationships").select(
            "*, child_article:contextual_articles!child_article_id(*)"
        ).eq(
            "parent_article_id", article_uuid
        ).order(
            "similarity_score", desc=True
        ).limit(max_results).execute()
        
        child_result = client.client.table("article_relationships").select(
            "*, parent_article:contextual_articles!parent_article_id(*)"
        ).eq(
            "child_article_id", article_uuid
        ).order(
            "similarity_score", desc=True
        ).limit(max_results).execute()
        
        # Combine and format results
        related_articles = []
        
        if parent_result.data:
            for rel in parent_result.data:
                related_articles.append({
                    "article": rel["child_article"],
                    "relationship_type": rel["relationship_type"],
                    "similarity_score": rel["similarity_score"],
                    "reasoning": rel.get("reasoning"),
                    "direction": "child"
                })
        
        if child_result.data:
            for rel in child_result.data:
                related_articles.append({
                    "article": rel["parent_article"],
                    "relationship_type": rel["relationship_type"],
                    "similarity_score": rel["similarity_score"],
                    "reasoning": rel.get("reasoning"),
                    "direction": "parent"
                })
        
        # Sort by similarity score and limit
        related_articles.sort(key=lambda x: x["similarity_score"], reverse=True)
        return related_articles[:max_results]
        
    except Exception as e:
        logger.error(f"Error finding related articles: {e}")
        return []