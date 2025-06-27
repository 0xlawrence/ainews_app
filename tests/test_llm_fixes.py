#!/usr/bin/env python3
"""
Test script to verify that the LLM router fixes are working properly.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from src.llm.llm_router import LLMRouter

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

async def test_fixes():
    # Load environment variables
    load_dotenv()
    
    # Initialize router  
    router = LLMRouter()
    
    # Test article data
    test_article = {
        'title': 'OpenAI Releases New GPT-4 Turbo Model with Enhanced Capabilities',
        'content': 'OpenAI has announced the release of GPT-4 Turbo, featuring improved reasoning capabilities and a larger context window. The new model demonstrates significant improvements in coding tasks and mathematical problem-solving.',
        'url': 'https://example.com/test-article',
        'source': 'tech_news'
    }
    
    try:
        print('Testing LLM router with real API call...')
        
        # Test summary generation
        summary = await router.generate_summary(
            article_title=test_article['title'],
            article_content=test_article['content'], 
            article_url=test_article['url'],
            source_name=test_article['source']
        )
        
        print(f'✅ Summary generated successfully!')
        print(f'Model used: {summary.model_used}')
        print(f'Confidence: {summary.confidence_score}')
        print(f'Summary points: {len(summary.summary_points)}')
        
        # Verify this is NOT a fallback
        is_real_llm = summary.model_used != 'fallback'
        print(f'Real LLM used (not fallback): {is_real_llm}')
        
        if is_real_llm:
            print('🎉 SUCCESS: LLM calls are now working properly!')
            for i, point in enumerate(summary.summary_points, 1):
                print(f'  {i}. {point}')
        else:
            print('❌ FAILURE: Still falling back to generic content')
            
    except Exception as e:
        print(f'❌ Test failed with error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_fixes())