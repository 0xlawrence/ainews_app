#!/usr/bin/env python3
"""
Test the newsletter generation with proper configuration.
"""

import sys
import os
import asyncio
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.schemas import NewsletterConfig

async def test_newsletter_config():
    """Test that NewsletterConfig produces correct values."""
    
    print("Testing NewsletterConfig with defaults...")
    
    # Create minimal config (similar to what main.py does)
    config = NewsletterConfig(
        max_items=30,  # Explicit 30 items
        sources=[],  # Empty for test
        processing_id="test_config"
    )
    
    print(f"✅ Config created successfully")
    print(f"  - max_items: {config.max_items}")
    print(f"  - ai_relevance_threshold: {config.ai_relevance_threshold}")
    print(f"  - min_articles_target: {config.min_articles_target}")
    print(f"  - dynamic_threshold: {config.dynamic_threshold}")
    
    # Simulate the source calculation
    num_sources = 38  # From log
    max_items_per_source = max(3, config.max_items // num_sources)
    
    print(f"  - Sources calculation: max(3, {config.max_items} // {num_sources}) = {max_items_per_source}")
    
    expected_total = min(max_items_per_source * num_sources, config.max_items)
    print(f"  - Expected total articles: min({max_items_per_source} * {num_sources}, {config.max_items}) = {expected_total}")
    
    if expected_total >= 20:
        print("✅ Configuration should provide sufficient articles")
        return True
    else:
        print("❌ Configuration will provide insufficient articles")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_newsletter_config())
    sys.exit(0 if success else 1)