#!/usr/bin/env python3
"""
AI News Newsletter Generator - Main Entry Point

This script generates AI news newsletters by:
1. Fetching RSS feeds and YouTube content
2. Filtering AI-related content
3. Summarizing with LLM (Gemini -> Claude -> GPT-4o fallback)
4. Removing duplicates
5. Generating Markdown newsletter

Usage:
    python main.py --max-items 30 --edition daily
    python main.py --max-items 30 --edition daily --output-dir drafts/
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import click
import structlog
import argparse

from src.workflow.newsletter_workflow import create_newsletter_workflow
from src.models.schemas import NewsletterConfig, ProcessingLog
from src.config.settings import get_settings
from src.utils.logger import setup_logging


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime and Pydantic objects."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, ProcessingLog):
            return {
                "processing_id": obj.processing_id,
                "timestamp": obj.timestamp.isoformat() if obj.timestamp else None,
                "stage": obj.stage,
                "event_type": obj.event_type,
                "message": obj.message,
                "data": obj.data,
                "duration_seconds": obj.duration_seconds
            }
        elif hasattr(obj, 'model_dump'):
            # Handle Pydantic models
            try:
                return obj.model_dump()
            except Exception:
                return str(obj)
        return super().default(obj)

# ---------------------------------------------------------------------------
# Load environment variables from .env if present (development convenience)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    # python-dotenv is optional in production (env vars set by CI/CD)
    pass

# Setup structured logging
logger = setup_logging()


def main():
    parser = argparse.ArgumentParser(description="AI News Newsletter Generator")
    parser.add_argument("--max-items", type=int, default=30, help="Maximum number of items to process")
    parser.add_argument("--edition", type=str, default="daily", help="Newsletter edition type")
    parser.add_argument("--output-dir", type=str, default="drafts", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no API calls)")
    parser.add_argument("--embedding-model", type=str, default="text-embedding-3-small", 
                       choices=["text-embedding-3-small", "text-embedding-3-large"],
                       help="OpenAI embedding model to use")
    parser.add_argument("--embedding-dimensions", type=int, 
                       help="Embedding dimensions (for text-embedding-3-large: 256, 1024, 3072)")
    
    args = parser.parse_args()
    
    # Set embedding dimensions based on model if not specified
    if args.embedding_dimensions is None:
        if args.embedding_model == "text-embedding-3-small":
            args.embedding_dimensions = 1536
        else:  # text-embedding-3-large
            args.embedding_dimensions = 1024  # Default to compressed version
    
    logger.info(
        "Starting newsletter generation",
        max_items=args.max_items,
        edition=args.edition,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        embedding_model=args.embedding_model,
        embedding_dimensions=args.embedding_dimensions
    )
    
    # Validate settings - this will raise validation errors if required vars are missing
    if not args.dry_run:
        try:
            settings = get_settings()
            # Test that we can access all required settings
            _ = settings.llm.openai_api_key
            _ = settings.llm.gemini_api_key  
            _ = settings.llm.claude_api_key
            _ = settings.database.supabase_url
            _ = settings.database.supabase_key
        except Exception as e:
            logger.error("Configuration validation failed", error=str(e))
            raise click.ClickException(f"Configuration error: {str(e)}")
    
    # Load sources configuration
    sources_path = Path("sources.json")
    if not sources_path.exists():
        logger.error("Sources file not found", path=str(sources_path))
        raise click.ClickException(f"Sources file not found: {sources_path}")
    
    with open(sources_path, 'r', encoding='utf-8') as f:
        sources_config = json.load(f)
    
    # Create output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create newsletter configuration
    config = NewsletterConfig(
        max_items=args.max_items,
        edition=args.edition,
        output_dir=str(output_path),
        sources=sources_config["sources"],
        dry_run=args.dry_run,
        embedding_model=args.embedding_model,
        embedding_dimensions=args.embedding_dimensions,
        processing_id=f"newsletter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    
    logger.info(
        "Starting newsletter generation",
        config=config.model_dump(),
        timestamp=datetime.now().isoformat()
    )
    
    try:
        # Run the newsletter workflow
        result = asyncio.run(run_newsletter_workflow(config))
        
        if result["status"] == "success":
            logger.info(
                "Newsletter generation completed successfully",
                output_file=result.get("output_file"),
                processing_time=result.get("processing_time_seconds"),
                articles_processed=result.get("articles_processed")
            )
            
            click.echo(f"✅ Newsletter generated: {result.get('output_file')}")
            click.echo(f"📊 Articles processed: {result.get('articles_processed')}")
            click.echo(f"⏱️  Processing time: {result.get('processing_time_seconds')}s")
            
        else:
            logger.error(
                "Newsletter generation failed",
                error=result.get("error"),
                processing_id=config.processing_id
            )
            raise click.ClickException(f"Generation failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(
            "Unexpected error during newsletter generation",
            error=str(e),
            processing_id=config.processing_id,
            exc_info=True
        )
        raise click.ClickException(f"Unexpected error: {str(e)}")


async def run_newsletter_workflow(config: NewsletterConfig) -> Dict:
    """Run the newsletter generation workflow."""
    start_time = datetime.now()
    
    try:
        # Create workflow instance first
        from src.workflow.newsletter_workflow import NewsletterWorkflow
        workflow_instance = NewsletterWorkflow()
        
        # Initialize with past articles
        await workflow_instance.initialize_with_past_articles(days_back=7)
        
        # Create and compile the workflow
        workflow = create_newsletter_workflow()
        
        # Initialize workflow state
        initial_state = {
            "config": config,
            "raw_articles": [],
            "filtered_articles": [],
            "summarized_articles": [],
            "deduplicated_articles": [],
            "clustered_articles": [],
            "final_newsletter": "",
            "processing_logs": [],
            "status": "starting"
        }
        
        # Execute workflow
        final_state = await workflow.ainvoke(initial_state)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Save processing logs
        log_file = Path("logs") / f"newsletter_{datetime.now().strftime('%Y-%m-%d')}.json"
        log_file.parent.mkdir(exist_ok=True)
        
        processing_log = {
            "processing_id": config.processing_id,
            "timestamp": start_time.isoformat(),
            "status": final_state.get("status", "unknown"),
            "execution_time_seconds": processing_time,
            "config": config.model_dump(),
            "processing_logs": final_state.get("processing_logs", []),
            "final_state": {
                "articles_processed": len(final_state.get("summarized_articles", [])),
                "articles_final": len(final_state.get("clustered_articles", [])),
                "newsletter_length": len(final_state.get("final_newsletter", "")),
            }
        }
        
        if not config.dry_run:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(processing_log, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
        
        return {
            "status": "success",
            "output_file": final_state.get("output_file"),
            "processing_time_seconds": processing_time,
            "articles_processed": len(final_state.get("summarized_articles", [])),
            "processing_id": config.processing_id
        }
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "status": "error",
            "error": str(e),
            "processing_time_seconds": processing_time,
            "processing_id": config.processing_id
        }


if __name__ == "__main__":
    main()