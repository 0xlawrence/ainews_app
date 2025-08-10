"""
Static constants for tests expecting constants.settings module.

These values mirror defaults from settings.py to satisfy unit tests.
"""

TEXT_LIMITS = {
    'toc_short': 50,
    'title_short': 70,
    'citation_max': 140,
    'summary_point_max': 150,
    'summary_point_min': 30,
}

SIMILARITY_THRESHOLDS = {
    'duplicate_jaccard': 0.70,
    'duplicate_sequence': 0.85,
    'duplicate_main': 0.85,
    'context_similarity': 0.60,
    'ai_relevance_high': 0.80,
}

PERFORMANCE = {
    'max_concurrent_llm': 5,
    'max_concurrent_citations': 5,
    'semaphore_limit': 5,
    'cache_max_size': 1000,
}

NEWSLETTER = {
    'max_citations_per_article': 3,
    'target_article_count': 7,
    'max_articles_processing': 30,
    'lead_text_sentences': 2,
}

LLM_SETTINGS = {
    'retry_delay': 1,
    'max_retries': 3,
    'timeout_seconds': 30,
    'summary_max_tokens': 1000,
    'temperature_conservative': 0.3,
}


