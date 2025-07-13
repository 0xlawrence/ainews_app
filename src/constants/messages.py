"""
Centralized error messages, defaults, and text templates.

This module provides consistent messaging across the application.
"""

# Error messages
ERROR_MESSAGES = {
    'llm_generation_failed': "LLM生成に失敗しました",
    'translation_failed': "翻訳生成に失敗しました",
    'citation_generation_failed': "引用生成に失敗しました",
    'context_analysis_failed': "コンテキスト分析に失敗しました",
    'title_generation_failed': "タイトル生成に失敗しました",
    'duplicate_check_failed': "重複チェックに失敗しました",
    'article_processing_failed': "記事処理に失敗しました",
    'supabase_connection_failed': "Supabaseへの接続に失敗しました",
    'invalid_article_format': "記事フォーマットが無効です",
    'insufficient_content': "コンテンツが不足しています"
}

# Default fallback content
DEFAULT_CONTENT = {
    'summary_point_fallback': "AI技術の進展に関する最新動向として注目されています",
    'title_fallback': "AI関連の最新発表",
    'company_fallback': "AI関連企業",
    'translation_fallback': "AI技術分野の重要な発表についての詳細記事",
    'citation_fallback': "AI関連の注目すべき最新ニュースの詳細報告",
    'empty_newsletter': "# AI NEWS TLDR\n\n本日は注目すべきAI関連ニュースがございませんでした。\n"
}

# Status messages for logging
STATUS_MESSAGES = {
    'processing_started': "処理を開始しました",
    'processing_completed': "処理が完了しました",
    'article_skipped_duplicate': "重複記事のためスキップしました",
    'article_marked_update': "続報記事としてマークしました",
    'parallel_processing_started': "並列処理を開始しました",
    'citation_generation_completed': "引用生成が完了しました",
    'newsletter_generated': "ニュースレターが生成されました"
}

# Template phrases for title generation
TITLE_TEMPLATES = {
    'announcement': "{company}が{product}を発表",
    'launch': "{company}の{product}がローンチ",
    'update': "{product}の最新アップデート",
    'research': "{topic}分野での研究進展",
    'partnership': "{company1}と{company2}が提携",
    'investment': "{amount}の投資ラウンドを実施",
    'acquisition': "{company}が{target}を買収"
}

# Quality validation messages
VALIDATION_MESSAGES = {
    'content_too_short': "コンテンツが短すぎます",
    'content_too_long': "コンテンツが長すぎます",
    'forbidden_phrases_detected': "禁止フレーズが検出されました",
    'low_quality_score': "品質スコアが低すぎます",
    'invalid_format': "フォーマットが無効です",
    'missing_required_fields': "必須フィールドが不足しています"
}

# Success messages
SUCCESS_MESSAGES = {
    'article_processed': "記事が正常に処理されました",
    'citations_generated': "引用が正常に生成されました",
    'newsletter_created': "ニュースレターが正常に作成されました",
    'supabase_saved': "Supabaseに正常に保存されました",
    'parallel_processing_completed': "並列処理が正常に完了しました"
}

# Prompt templates for LLM operations
PROMPT_TEMPLATES = {
    'translation_request': """以下の英語記事のタイトルと要約から、高品質な引用文を日本語で生成してください。

記事情報:
タイトル: {title}
要約: {summary}

要求:
- 記事の重要ポイントを100文字で要約（タイトル翻訳ではなく内容の要点）
- 数値や固有名詞があれば必ず含める
- 自然で読みやすい日本語
- 具体的な成果や影響を記載

日本語引用文:""",

    'title_generation': """以下の記事から、魅力的な日本語タイトルを生成してください。

記事内容: {content}

要求:
- 50文字以内
- 具体的な企業名・技術名を含む
- 読者の興味を引く表現
- 体言止めで終わる

タイトル:""",

    'summary_generation': """以下の記事を3-4個の要点に要約してください。

記事内容: {content}

要求:
- 各要点は30-150文字
- 具体的な数値・企業名を含む
- 読みやすい日本語（です・ます調）
- 重要度順に並べる

要約:"""
}

# Regex patterns for text cleaning
CLEANING_PATTERNS = {
    'meta_removal': [
        r'^はい、?承知[いし]?[たま]*しました。.*?(\\*\\*翻訳[：:]?\\*\\*|【翻訳】|翻訳[：:])\\s*',
        r'^以下に.*?(\\*\\*翻訳[：:]?\\*\\*|【翻訳】|翻訳[：:])\\s*',
        r'^ご?要望に.*?(\\*\\*翻訳[：:]?\\*\\*|【翻訳】|翻訳[：:])\\s*',
        r'^\\*\\*翻訳[：:]?\\*\\*\\s*',
        r'^【翻訳】\\s*',
        r'^翻訳[：:]\\s*',
        r'^引用文?[：:]\\s*',
        r'^要約[：:]\\s*',
        r'^\\d+\\.\\s*'
    ],
    'title_prefixes': [
        r'^breaking[:\\s]*',
        r'^exclusive[:\\s]*',
        r'^report[:\\s]*',
        r'^[^:]+:\\s*',
        r'^\\w+\\s+\\w+\\s+(?:announces?|launches?|reveals?|unveils?)\\s+'
    ],
    'title_suffixes': [
        r'\\s*\\[update\\]$',
        r'\\s*\\(updated?\\)$',
        r'\\s*- report$',
        r'\\s*\\|\\s*[^|]+$'
    ],
    'duplicate_patterns': [
        # LLM tech term duplications
        r'(LLM)の([^のLLM]+)\\1',  # "LLMの技術LLM" -> "LLMの技術"
        r'(AI)の([^のAI]+)\\1',   # "AIの活用AI" -> "AIの活用"
        r'(GPT)の([^のGPT]+)\\1', # "GPTの機能GPT" -> "GPTの機能"
        r'(API)の([^のAPI]+)\\1', # "APIの実装API" -> "APIの実装"
        r'(SDK)の([^のSDK]+)\\1', # "SDKの利用SDK" -> "SDKの利用"

        # Tech terms with particles
        r'(LLM|AI|GPT|API|SDK)で\\1',    # "LLMでLLM" -> "LLM"
        r'(LLM|AI|GPT|API|SDK)が\\1',    # "AIがAI" -> "AI"
        r'(LLM|AI|GPT|API|SDK)を\\1',    # "GPTをGPT" -> "GPT"

        # Broader duplication patterns
        r'(\\w+)の(\\w+)で\\1',           # "技術の実装で技術" -> "技術の実装"
        r'(\\w+)による(\\w+)\\1',         # "AIによる開発AI" -> "AIによる開発"
        r'(\\w+)で(\\w+)の\\1',           # "開発で技術の開発" -> "開発で技術"

        # Company/product duplications
        r'(OpenAI|Anthropic|Google|Microsoft)の(\\w+)\\1',
        r'(ChatGPT|Claude|Gemini|Copilot)の(\\w+)\\1'
    ]
}
